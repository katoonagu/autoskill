# Runtime

Ephemeral operational state now lives here instead of under `automation/`.

- `runtime/state/` stores per-module state JSON and browser/runtime snapshots.
- `runtime/tasks/` stores control-plane task buckets.
- `runtime/decisions/` stores approval buckets.

Source code stays in `automation/`. Runtime data stays here.
