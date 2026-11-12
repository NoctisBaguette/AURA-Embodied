# M6 parent-report serialization repair

Date: 2026-10-06 (Asia/Shanghai).

The first native launch on scientific commit
`7059c713d3b36e3f032aab8d1f87662ed6fdab91` completed normal / seed 100 /
Baseline and printed evidence passed, eligible, endpoint task success true.
These are provisional runner outputs, not an independent native audit.
The parent then failed saving `suite.json` with
`TypeError: Object of type bool_ is not JSON serializable`.

The audit can retain NumPy booleans in its check dictionary. The parent passes
that dictionary to a strict JSON writer without scalar conversion. Fixture
sweep mocks used ordinary booleans and missed this transport failure. No
controller or simulator failure is established by this exception.

## Bounded correction

Export [tools/m6_reporting_resume.py](../../../tools/m6_reporting_resume.py)
outside the server checkout. Keep the clean scientific checkout at the original
commit above; do not merge the documentation/repair commit into that checkout.
Launcher SHA-256:
`c6ea9e36d89d56cb5fb738387092e23cb627016f22900c225b29040fa8731681`.

The launcher adapts only the parent writer through the existing `json_value`
converter. It preserves true/false values and rejects non-finite JSON numbers.
Native children still launch the unchanged `aether_cl.m6` module in fresh
interpreters. Scientific files, preregistration, seeds, budget, scoring,
comparisons, tolerances and child startup environment remain unchanged.

Initial repair accepts only the one-slot running report and exactly one
finished retained child. It requires the original plan, protocol, software,
environment, paths and full raw replay. It exclusively creates a backup of
the original report and all existing study bytes, records hashes/provenance,
then records the completed first slot. It never relaunches that child.
Incomplete, ambiguous or invalid evidence stops the operation.

Use `--repair-initial --backup <new-external-file> --stop-after 17` to complete
the retained first 18. Run the original `m6_sweep --check-pilot` gate. If valid,
launch the same reporting helper without initial-repair flags to continue the
unstarted slots. Its normal resume still uses every original source, software,
environment, raw-hash and replay guard. The helper identity and immutable
backup hash are checked again on continuation.

The archived suite records `reporting_repair`, the original scientific commit,
launcher digest, adopted slot, original file hashes and external backup digest.
Preserve the backup for independent audit. No outcome is excluded or replaced.

## Validation

Three focused regression tests reproduce the actual NumPy-boolean write crash,
reconstruct the complete first slot, continue to 18 distinct calls without a
rerun, verify backup/raw-byte preservation, pass the commissioning checks, and
reject software drift, incomplete/tampered child records and a second repair.
They also verify false/true preservation and retained NaN rejection. Python
3.10 syntax passes. The prior 121-test result remains the original engineering
validation; the focused tests validate this separate reporting correction.

## Audited completion

Native continuation and independent archive audit are complete. The before-repair
backup matches its recorded hash; every original non-parent file is unchanged
in the pilot and final archives. The completed first child was adopted once,
not rerun. All first-18 trial records and raw pilot files are preserved in the
360-slot final archive; both aggregate reports and CSVs reproduce exactly.

On reconnection, the initial repair guard rejected an environment mismatch.
Read-only diagnostics found only `XDG_SESSION_ID`, recorded 876 versus current
879. Exporting the recorded value reconstructed the exact original full child
environment hash; no guard was waived or rewritten. A separate pilot check
from base Conda failed to import SciPy, then passed under the original `aether-cl`
environment. Neither check changed measured trials.

The full study finishes with valid evidence, while all 62 required recovery
attempts abort before release. This scientific result is independent of the
reporting transport repair. See [audited results](AETHER_CL_M6_Results.md)
and [return to 02](AETHER_CL_M6_Return_to_02.md).
