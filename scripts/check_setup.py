from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def check_python() -> list[str]:
    problems: list[str] = []
    if sys.version_info < (3, 11):
        problems.append(
            f"Python 3.11+ is recommended, current version is {sys.version.split()[0]}"
        )
    return problems


def check_imports() -> list[str]:
    problems: list[str] = []
    try:
        import playwright  # noqa: F401
    except Exception as exc:
        problems.append(f"Playwright is not available: {exc}")
    return problems


def check_config() -> list[str]:
    problems: list[str] = []
    try:
        from automation.config import AdsPowerSettings

        AdsPowerSettings.from_project_root(PROJECT_ROOT)
    except Exception as exc:
        problems.append(str(exc))
    return problems


def check_adspower_status() -> list[str]:
    problems: list[str] = []
    try:
        from automation.adspower import AdsPowerClient
        from automation.config import AdsPowerSettings

        settings = AdsPowerSettings.from_project_root(PROJECT_ROOT)
        client = AdsPowerClient(settings)
        status = client.status()
        if not isinstance(status, dict):
            problems.append(f"Unexpected AdsPower status response: {status!r}")
    except Exception as exc:
        problems.append(f"AdsPower API check failed: {exc}")
    return problems


def main() -> int:
    checks = {
        "python": check_python(),
        "imports": check_imports(),
        "config": check_config(),
        "adspower": check_adspower_status(),
    }

    has_problems = False
    for name, problems in checks.items():
        if problems:
            has_problems = True
            print(f"[FAIL] {name}")
            for problem in problems:
                print(f"  - {problem}")
        else:
            print(f"[OK]   {name}")

    if has_problems:
        print("\nSetup is incomplete.")
        return 1

    print("\nSetup looks ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
