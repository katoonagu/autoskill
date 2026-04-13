from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import re
import urllib.error
import urllib.request


class LLMUnavailableError(RuntimeError):
    pass


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _load_env_values(project_root: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    values.update(_read_env_file(project_root / ".env"))
    values.update(_read_env_file(project_root / ".env.local"))
    return values


def _extract_json_object(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model response")
    return json.loads(stripped[start : end + 1])


@dataclass(frozen=True)
class AutoskillLLMConfig:
    provider: str
    openai_api_key: str
    gemini_api_key: str
    kie_openai_api_key: str
    kie_gemini_api_key: str
    brain_model: str
    writer_model: str
    media_model: str
    brain_reasoning_effort: str
    writer_reasoning_effort: str


class AutoskillLLMClient:
    def __init__(self, config: AutoskillLLMConfig):
        self.config = config

    @classmethod
    def from_project_root(cls, project_root: Path) -> "AutoskillLLMClient":
        values = _load_env_values(project_root)
        openai_key = os.environ.get("OPENAI_API_KEY") or values.get("OPENAI_API_KEY") or ""
        kie_openai_key = os.environ.get("KIE_OPENAI_API_KEY") or values.get("KIE_OPENAI_API_KEY") or ""
        google_gemini_key = os.environ.get("GEMINI_API_KEY") or values.get("GEMINI_API_KEY") or ""
        kie_gemini_key = os.environ.get("KIE_GEMINI_API_KEY") or values.get("KIE_GEMINI_API_KEY") or ""
        provider = (
            os.environ.get("AUTOSKILL_LLM_PROVIDER")
            or values.get("AUTOSKILL_LLM_PROVIDER")
            or ("openai" if (openai_key or kie_openai_key) else "gemini" if (kie_gemini_key or google_gemini_key) else "")
        ).strip().lower()
        config = AutoskillLLMConfig(
            provider=provider,
            openai_api_key=openai_key,
            gemini_api_key=google_gemini_key,
            kie_openai_api_key=kie_openai_key,
            kie_gemini_api_key=kie_gemini_key,
            brain_model=os.environ.get("AUTOSKILL_LLM_MODEL_BRAIN") or values.get("AUTOSKILL_LLM_MODEL_BRAIN") or "gpt-5.4",
            writer_model=os.environ.get("AUTOSKILL_LLM_MODEL_WRITER") or values.get("AUTOSKILL_LLM_MODEL_WRITER") or "gpt-5.4-mini",
            media_model=os.environ.get("AUTOSKILL_LLM_MODEL_MEDIA") or values.get("AUTOSKILL_LLM_MODEL_MEDIA") or "gemini-2.5-flash",
            brain_reasoning_effort=(
                os.environ.get("AUTOSKILL_LLM_REASONING_EFFORT_BRAIN")
                or values.get("AUTOSKILL_LLM_REASONING_EFFORT_BRAIN")
                or "high"
            ),
            writer_reasoning_effort=(
                os.environ.get("AUTOSKILL_LLM_REASONING_EFFORT_WRITER")
                or values.get("AUTOSKILL_LLM_REASONING_EFFORT_WRITER")
                or "low"
            ),
        )
        return cls(config)

    def is_available(self) -> bool:
        if self.config.provider == "openai":
            return bool(self.config.openai_api_key or self.config.kie_openai_api_key)
        if self.config.provider == "gemini":
            return bool(self.config.kie_gemini_api_key or self.config.gemini_api_key)
        return False

    def generate_structured(self, prompt: str, schema: dict, model: str | None = None, temperature: float = 0) -> dict:
        if not self.is_available():
            raise LLMUnavailableError("No configured LLM provider or API key for structured generation")
        schema_text = json.dumps(schema, ensure_ascii=False)
        wrapped_prompt = (
            f"{prompt}\n\n"
            "Верни только валидный JSON без пояснений и без markdown fences.\n"
            f"Schema:\n{schema_text}"
        )
        if self.config.provider == "openai":
            return self._generate_openai_structured_with_fallback(wrapped_prompt, model or self.config.brain_model, temperature)
        if self.config.provider == "gemini":
            return self._generate_media_json_with_fallback(wrapped_prompt, model or self.config.media_model, temperature)
        raise LLMUnavailableError(f"Unsupported LLM provider: {self.config.provider}")

    def generate_text(self, prompt: str, model: str | None = None, temperature: float = 0) -> str:
        if not self.is_available():
            raise LLMUnavailableError("No configured LLM provider or API key for text generation")
        if self.config.provider == "openai":
            return self._generate_openai_text_with_fallback(prompt, model or self.config.writer_model, temperature)
        if self.config.provider == "gemini":
            return self._generate_media_text_with_fallback(prompt, model or self.config.media_model, temperature)
        raise LLMUnavailableError(f"Unsupported LLM provider: {self.config.provider}")

    def analyze_media(self, payload: dict, schema: dict, model: str | None = None) -> dict:
        prompt = json.dumps(payload, ensure_ascii=False, indent=2)
        return self._generate_media_json_with_fallback(prompt, model or self.config.media_model, temperature=0)

    def _generate_openai_structured_with_fallback(self, prompt: str, model: str, temperature: float) -> dict:
        if self.config.openai_api_key:
            try:
                return self._openai_generate_json(prompt, model, temperature)
            except RuntimeError as exc:
                if not self._should_fallback_to_kie(exc):
                    raise
        if self.config.kie_openai_api_key:
            return self._kie_responses_generate_json(prompt, model, temperature, reasoning_effort=self.config.brain_reasoning_effort)
        raise LLMUnavailableError("OpenAI is unavailable and no KIE OpenAI fallback key is configured")

    def _generate_openai_text_with_fallback(self, prompt: str, model: str, temperature: float) -> str:
        if self.config.openai_api_key:
            try:
                return self._openai_generate_text(prompt, model, temperature)
            except RuntimeError as exc:
                if not self._should_fallback_to_kie(exc):
                    raise
        if self.config.kie_openai_api_key:
            reasoning_effort = self.config.brain_reasoning_effort if model == self.config.brain_model else self.config.writer_reasoning_effort
            return self._kie_responses_generate_text(prompt, model, temperature, reasoning_effort=reasoning_effort)
        raise LLMUnavailableError("OpenAI is unavailable and no KIE OpenAI fallback key is configured")

    def _generate_media_json_with_fallback(self, prompt: str, model: str, temperature: float) -> dict:
        if self.config.kie_gemini_api_key:
            return self._kie_gemini_generate_json(prompt, model, temperature)
        if self.config.gemini_api_key:
            return self._gemini_generate_json(prompt, model, temperature)
        if self.config.kie_openai_api_key:
            return self._kie_responses_generate_json(prompt, self.config.brain_model, temperature, reasoning_effort=self.config.brain_reasoning_effort)
        raise LLMUnavailableError("No media-capable LLM key configured")

    def _generate_media_text_with_fallback(self, prompt: str, model: str, temperature: float) -> str:
        if self.config.kie_gemini_api_key:
            return self._kie_gemini_generate_text(prompt, model, temperature)
        if self.config.gemini_api_key:
            return self._gemini_generate_text(prompt, model, temperature)
        if self.config.kie_openai_api_key:
            return self._kie_responses_generate_text(prompt, self.config.brain_model, temperature, reasoning_effort=self.config.brain_reasoning_effort)
        raise LLMUnavailableError("No media-capable LLM key configured")

    def _should_fallback_to_kie(self, exc: RuntimeError) -> bool:
        message = str(exc).lower()
        return any(
            marker in message
            for marker in (
                "insufficient_quota",
                "quota",
                "billing",
                "credit balance",
                "credits",
                "429",
                "rate limit",
            )
        )

    def _openai_generate_text(self, prompt: str, model: str, temperature: float) -> str:
        body = {
            "model": model,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        payload = self._post_json(
            "https://api.openai.com/v1/chat/completions",
            body,
            headers={"Authorization": f"Bearer {self.config.openai_api_key}"},
        )
        return str((((payload.get("choices") or [{}])[0].get("message") or {}).get("content")) or "")

    def _openai_generate_json(self, prompt: str, model: str, temperature: float) -> dict:
        body = {
            "model": model,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": prompt}],
        }
        payload = self._post_json(
            "https://api.openai.com/v1/chat/completions",
            body,
            headers={"Authorization": f"Bearer {self.config.openai_api_key}"},
        )
        content = str((((payload.get("choices") or [{}])[0].get("message") or {}).get("content")) or "")
        return _extract_json_object(content)

    def _kie_responses_generate_text(self, prompt: str, model: str, temperature: float, *, reasoning_effort: str) -> str:
        payload = self._post_json(
            "https://api.kie.ai/codex/v1/responses",
            {
                "model": model,
                "stream": False,
                "input": [
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": prompt}],
                    }
                ],
                "reasoning": {"effort": reasoning_effort},
                "temperature": temperature,
            },
            headers={"Authorization": f"Bearer {self.config.kie_openai_api_key}"},
        )
        return self._extract_responses_output_text(payload)

    def _kie_responses_generate_json(self, prompt: str, model: str, temperature: float, *, reasoning_effort: str) -> dict:
        text = self._kie_responses_generate_text(prompt, model, temperature, reasoning_effort=reasoning_effort)
        return _extract_json_object(text)

    def _kie_gemini_generate_text(self, prompt: str, model: str, temperature: float) -> str:
        payload = self._post_json(
            f"https://api.kie.ai/{model}/v1/chat/completions",
            {
                "model": model,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            },
            headers={"Authorization": f"Bearer {self.config.kie_gemini_api_key}"},
        )
        return str((((payload.get("choices") or [{}])[0].get("message") or {}).get("content")) or "")

    def _kie_gemini_generate_json(self, prompt: str, model: str, temperature: float) -> dict:
        payload = self._post_json(
            f"https://api.kie.ai/{model}/v1/chat/completions",
            {
                "model": model,
                "temperature": temperature,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": prompt}],
            },
            headers={"Authorization": f"Bearer {self.config.kie_gemini_api_key}"},
        )
        content = str((((payload.get("choices") or [{}])[0].get("message") or {}).get("content")) or "")
        return _extract_json_object(content)

    def _gemini_generate_text(self, prompt: str, model: str, temperature: float) -> str:
        payload = self._post_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.config.gemini_api_key}",
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": temperature},
            },
        )
        return self._extract_gemini_text(payload)

    def _gemini_generate_json(self, prompt: str, model: str, temperature: float) -> dict:
        text = self._gemini_generate_text(prompt, model, temperature)
        return _extract_json_object(text)

    def _extract_gemini_text(self, payload: dict) -> str:
        candidates = payload.get("candidates") or []
        parts = ((((candidates[0] if candidates else {}).get("content") or {}).get("parts")) or [])
        return "\n".join(str(part.get("text") or "") for part in parts if part.get("text"))

    def _extract_responses_output_text(self, payload: dict) -> str:
        output_items = payload.get("output") or []
        collected: list[str] = []
        for item in output_items:
            if item.get("type") != "message":
                continue
            for content in item.get("content") or []:
                text = str(content.get("text") or "")
                if text:
                    collected.append(text)
        return "\n".join(collected).strip()

    def _post_json(self, url: str, payload: dict, headers: dict[str, str] | None = None) -> dict:
        merged_headers = {"Content-Type": "application/json"}
        merged_headers.update(headers or {})
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=merged_headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "ignore")
            raise RuntimeError(f"LLM request failed: {exc.code} {body}") from exc
