# Required engineering checks

Before any code implementation or review, read the latest versions of these
files through authenticated GitHub access:

- `NoctisBaguette/Embodied-AI-Research/engineering/INCIDENT_REGISTER.md`
- `NoctisBaguette/Embodied-AI-Research/engineering/CODE_CHANGE_PROTOCOL.md`

The incident register is private. Do not copy its detailed contents into this
public checkout, issues, PR descriptions, bundles, logs or artifacts. Record new
assistant-created defects and missed review checks in the private register during
the same work session. Retain the original entry, evidence and recurrence links;
do not silently erase a failure or mark an unverified repair closed.

If access fails, report the limitation and continue useful authorized diagnostics
from available evidence. Do not claim to have read inaccessible records. User
authorization and the current scientific scope still govern the work.

Inspect real producer and consumer interfaces before changing them. Verify actual
field names, scalar types, array shapes, units, batch-dependent caches and process
boundaries. Exercise the boundary with representative producer output, rather
than a mock that repeats the implementation's assumption. Review every affected
call site and the final diff before publishing.

Distinguish unit tests, source inspection, native prerequisite checks and observed
end-to-end execution. Resolve known runtime prerequisite failures before giving
another native rollout command; read-only diagnosis may proceed. Do not present
a test count as proof of an untested integration.

Preserve failed attempts and immutable archives. Never replace native outcomes,
spend fresh seeds, relax scoring gates or modify frozen scientific sources to
hide a reporting or deployment failure. Any continuation must identify and retain
the original attempt and follow the current scope and retry rules.

For server commands, verify the active checkout, shell, complete environment
setup and retained receipts. If a job needs stopping, identify that exact owned
job; do not kill unrelated processes. State whether visual evidence is actual
camera rendering, recorded replay or a reconstruction from saved state.
