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
    brain_model: str
    writer_model: str
    media_model: str


class AutoskillLLMClient:
    def __init__(self, config: AutoskillLLMConfig):
        self.config = config

    @classmethod
    def from_project_root(cls, project_root: Path) -> "AutoskillLLMClient":
        values = _load_env_values(project_root)
        config = AutoskillLLMConfig(
            provider=(
                os.environ.get("AUTOSKILL_LLM_PROVIDER")
                or values.get("AUTOSKILL_LLM_PROVIDER")
                or ("openai" if (os.environ.get("OPENAI_API_KEY") or values.get("OPENAI_API_KEY")) else "gemini" if (os.environ.get("GEMINI_API_KEY") or values.get("GEMINI_API_KEY")) else "")
            ).strip().lower(),
            openai_api_key=os.environ.get("OPENAI_API_KEY") or values.get("OPENAI_API_KEY") or "",
            gemini_api_key=os.environ.get("GEMINI_API_KEY") or values.get("GEMINI_API_KEY") or "",
            brain_model=os.environ.get("AUTOSKILL_LLM_MODEL_BRAIN") or values.get("AUTOSKILL_LLM_MODEL_BRAIN") or "gpt-4o-mini",
            writer_model=os.environ.get("AUTOSKILL_LLM_MODEL_WRITER") or values.get("AUTOSKILL_LLM_MODEL_WRITER") or "gpt-4o-mini",
            media_model=os.environ.get("AUTOSKILL_LLM_MODEL_MEDIA") or values.get("AUTOSKILL_LLM_MODEL_MEDIA") or "gemini-2.0-flash",
        )
        return cls(config)

    def is_available(self) -> bool:
        if self.config.provider == "openai":
            return bool(self.config.openai_api_key)
        if self.config.provider == "gemini":
            return bool(self.config.gemini_api_key)
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
            return self._openai_generate_json(wrapped_prompt, model or self.config.brain_model, temperature)
        if self.config.provider == "gemini":
            return self._gemini_generate_json(wrapped_prompt, model or self.config.brain_model, temperature)
        raise LLMUnavailableError(f"Unsupported LLM provider: {self.config.provider}")

    def generate_text(self, prompt: str, model: str | None = None, temperature: float = 0) -> str:
        if not self.is_available():
            raise LLMUnavailableError("No configured LLM provider or API key for text generation")
        if self.config.provider == "openai":
            return self._openai_generate_text(prompt, model or self.config.writer_model, temperature)
        if self.config.provider == "gemini":
            return self._gemini_generate_text(prompt, model or self.config.writer_model, temperature)
        raise LLMUnavailableError(f"Unsupported LLM provider: {self.config.provider}")

    def analyze_media(self, payload: dict, schema: dict, model: str | None = None) -> dict:
        return self.generate_structured(
            prompt=json.dumps(payload, ensure_ascii=False, indent=2),
            schema=schema,
            model=model or self.config.media_model,
            temperature=0,
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
