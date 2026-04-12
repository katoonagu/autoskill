from __future__ import annotations

from dataclasses import dataclass
import json
from urllib import request

from .config import AdsPowerSettings


@dataclass(frozen=True)
class ProfileInfo:
    profile_id: str
    profile_no: str
    name: str
    proxy_id: str
    proxy_host: str
    proxy_port: str


@dataclass(frozen=True)
class ProxyInfo:
    proxy_id: str
    proxy_type: str
    host: str
    port: str
    remark: str
    profile_count: str


@dataclass(frozen=True)
class StartedProfile:
    ws_puppeteer: str
    debug_port: str
    webdriver_path: str


class AdsPowerClient:
    def __init__(self, settings: AdsPowerSettings):
        self.settings = settings

    def _http_json(self, path: str, method: str = "GET", payload: dict | None = None) -> dict:
        url = f"{self.settings.base_url}{path}"
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")

        req = request.Request(
            url,
            data=body,
            method=method,
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
            },
        )
        with request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))

    def status(self) -> dict:
        return self._http_json("/status")

    def stop_profile(self, profile_no: str | None = None, profile_id: str | None = None) -> dict:
        payload: dict[str, str] = {}
        if profile_id:
            payload["profile_id"] = profile_id
        else:
            payload["profile_no"] = profile_no or self.settings.profile_no
        return self._http_json("/api/v2/browser-profile/stop", method="POST", payload=payload)

    def get_profile(self, profile_no: str | None = None) -> ProfileInfo:
        payload = {
            "profile_no": [profile_no or self.settings.profile_no],
            "page": 1,
            "page_size": 1,
        }
        data = self._http_json("/api/v2/browser-profile/list", method="POST", payload=payload)
        if data.get("code") != 0:
            raise RuntimeError(f"AdsPower get_profile failed: {data}")
        items = ((data.get("data") or {}).get("list") or [])
        if not items:
            raise RuntimeError(f"AdsPower profile not found for profile_no={profile_no or self.settings.profile_no}")
        item = items[0]
        return ProfileInfo(
            profile_id=str(item.get("profile_id") or ""),
            profile_no=str(item.get("profile_no") or item.get("serial_number") or ""),
            name=str(item.get("name") or ""),
            proxy_id=str(item.get("fbcc_proxy_acc_id") or item.get("proxy_id") or item.get("proxyid") or ""),
            proxy_host=str(((item.get("user_proxy_config") or {}).get("proxy_host")) or ""),
            proxy_port=str(((item.get("user_proxy_config") or {}).get("proxy_port")) or ""),
        )

    def list_proxies(self, *, page: int = 1, limit: int = 50) -> list[ProxyInfo]:
        payload = {"page": page, "limit": limit}
        data = self._http_json("/api/v2/proxy-list/list", method="POST", payload=payload)
        if data.get("code") != 0:
            raise RuntimeError(f"AdsPower list_proxies failed: {data}")
        items = ((data.get("data") or {}).get("list") or [])
        return [
            ProxyInfo(
                proxy_id=str(item.get("proxy_id") or ""),
                proxy_type=str(item.get("type") or ""),
                host=str(item.get("host") or ""),
                port=str(item.get("port") or ""),
                remark=str(item.get("remark") or ""),
                profile_count=str(item.get("profile_count") or ""),
            )
            for item in items
        ]

    def update_profile_proxy(self, *, profile_id: str, proxy_id: str) -> dict:
        payload = {"profile_id": profile_id, "proxyid": proxy_id}
        return self._http_json("/api/v2/browser-profile/update", method="POST", payload=payload)

    def clear_profile_proxy(self, *, profile_id: str) -> dict:
        payload = {
            "profile_id": profile_id,
            "user_proxy_config": {"proxy_soft": "no_proxy"},
        }
        return self._http_json("/api/v2/browser-profile/update", method="POST", payload=payload)

    def start_profile(
        self,
        profile_no: str | None = None,
        *,
        headless: bool = False,
        last_opened_tabs: bool = False,
        proxy_detection: bool = False,
    ) -> StartedProfile:
        payload = {
            "profile_no": profile_no or self.settings.profile_no,
            "headless": "1" if headless else "0",
            "last_opened_tabs": "1" if last_opened_tabs else "0",
            "proxy_detection": "1" if proxy_detection else "0",
        }
        data = self._http_json("/api/v2/browser-profile/start", method="POST", payload=payload)
        if data.get("code") != 0 or "data" not in data:
            raise RuntimeError(f"AdsPower start_profile failed: {data}")

        payload_data = data["data"]
        return StartedProfile(
            ws_puppeteer=payload_data["ws"]["puppeteer"],
            debug_port=str(payload_data["debug_port"]),
            webdriver_path=payload_data["webdriver"],
        )
