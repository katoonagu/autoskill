from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve()
while not (PROJECT_ROOT / "automation").exists() and PROJECT_ROOT.parent != PROJECT_ROOT:
    PROJECT_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from automation.adspower import AdsPowerClient
from automation.config import AdsPowerSettings


def main() -> None:
    settings = AdsPowerSettings.from_project_root(PROJECT_ROOT)
    client = AdsPowerClient(settings)

    before = client.get_profile()
    proxies = client.list_proxies(limit=50)
    candidates = [proxy for proxy in proxies if proxy.proxy_id and proxy.proxy_id != before.proxy_id]
    if not candidates:
        raise RuntimeError("No alternate proxies available in AdsPower proxy list")

    candidate = candidates[0]
    print(f"Profile before: profile_no={before.profile_no} profile_id={before.profile_id} proxy_id={before.proxy_id!r}")
    print(
        "Selected fallback proxy: "
        f"proxy_id={candidate.proxy_id} type={candidate.proxy_type} host={candidate.host}:{candidate.port} "
        f"remark={candidate.remark!r} profile_count={candidate.profile_count}"
    )

    try:
        stop_result = client.stop_profile(profile_no=before.profile_no)
        print(f"Stop profile result: {stop_result}")
    except Exception as exc:
        print(f"Stop profile raised: {exc}")

    try:
        update_result = client.update_profile_proxy(profile_id=before.profile_id, proxy_id=candidate.proxy_id)
        print(f"Update proxy result: {update_result}")

        after = client.get_profile(before.profile_no)
        print(f"Profile after update: profile_no={after.profile_no} profile_id={after.profile_id} proxy_id={after.proxy_id!r}")

        try:
            started = client.start_profile(profile_no=before.profile_no, last_opened_tabs=True)
            print(
                "Start profile result: "
                f"debug_port={started.debug_port} ws_puppeteer={started.ws_puppeteer}"
            )
        except Exception as exc:
            print(f"Start profile raised: {exc}")
    finally:
        if before.proxy_id:
            restore_result = client.update_profile_proxy(profile_id=before.profile_id, proxy_id=before.proxy_id)
        else:
            restore_result = client.clear_profile_proxy(profile_id=before.profile_id)
        restored = client.get_profile(before.profile_no)
        print(f"Restore proxy result: {restore_result}")
        print(
            "Profile after restore: "
            f"profile_no={restored.profile_no} profile_id={restored.profile_id} proxy_id={restored.proxy_id!r}"
        )


if __name__ == "__main__":
    main()

