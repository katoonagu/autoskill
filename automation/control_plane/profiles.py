from __future__ import annotations

from .models import ProfileLease, ProfilePoolEntry
from .storage import ControlPlanePaths, read_json, utcnow_iso, write_json


def _lease_path(paths: ControlPlanePaths, profile_key: str):
    return paths.state_root / "leases" / f"{profile_key}.json"


def load_profile_lease(paths: ControlPlanePaths, profile_key: str):
    path = _lease_path(paths, profile_key)
    if not path.exists():
        return None
    return ProfileLease.from_dict(read_json(path))


def acquire_profile_lease(
    paths: ControlPlanePaths,
    *,
    pool: dict[str, ProfilePoolEntry],
    capability: str,
    task_id: str,
    agent: str,
):
    for profile_key, entry in pool.items():
        if entry.capability != capability:
            continue
        current = load_profile_lease(paths, profile_key)
        if entry.exclusive and current is not None and not current.released_at_iso:
            continue
        lease = ProfileLease(
            profile_key=profile_key,
            capability=entry.capability,
            profile_no=entry.profile_no,
            task_id=task_id,
            agent=agent,
            leased_at_iso=utcnow_iso(),
        )
        write_json(_lease_path(paths, profile_key), lease.to_dict())
        return lease
    return None


def release_profile_lease(paths: ControlPlanePaths, *, profile_key: str) -> None:
    path = _lease_path(paths, profile_key)
    if not path.exists():
        return
    lease = ProfileLease.from_dict(read_json(path))
    lease.released_at_iso = utcnow_iso()
    write_json(path, lease.to_dict())
