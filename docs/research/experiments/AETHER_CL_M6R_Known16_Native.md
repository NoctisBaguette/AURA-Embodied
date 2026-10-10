# M6R known16 native commissioning audit

Date: 2026-10-06 (Asia/Shanghai).

Subsequent status: the [fresh matrix and independent audit](AETHER_CL_M6R_Results.md)
are complete. [Return to 02](AETHER_CL_M6R_Return_to_02.md). The next-step section
below records the transition authorized by this earlier development audit.

The returned native development archive passes independent raw replay and the
preregistered commissioning gate. Proceed with the unchanged frozen 480-slot
study on seeds 120–139. These 16 known-seed trials are development evidence,
not confirmatory results and not part of that fresh matrix.

## Provenance and audit

Native measurement revision: `9ac5439e003f2ed65ecf2ea02f59a6186c7b6714`, clean.
Python 3.10.22, NumPy 1.26.4, ManiSkill 3.0.1, SAPIEN 3.0.3; same native stack
and private GL environment as M6. All five upstream native source identities
match across the 16 children and the retained M6 counterparts. The archive
contains exactly the selected normal/8 cm × seeds 100/101 × four-system matrix.

| Evidence | Value |
| --- | --- |
| Archive | `aether-cl-m6r-known-commission.tar.gz` |
| Bytes | 3,868,647 |
| Archive SHA-256 | `779b8cc01ab2f0c47ff4d7a407750c20a17fd46f98bf93fc3726bf38eb912bb1` |
| Log SHA-256 | `f94c076c1c356ca0ce4767784a88de5a8199383fe14838d09a0d868b4fa0b27b` |
| Suite SHA-256 | `37afe1092838504b541ce2e7c0ecda665ce1799fd486b83c988ea75a3640a63d` |
| Indexed files checked | 84, with exact file-set, sizes and raw hashes |
| Complete child replays | 16, no exclusions, 800 actions each |
| Actions replayed | 12,800; maximum action error exactly zero |
| Comparisons reconstructed | 4 passive, 4 recovery, 4 repair, 2 control |

The auditor checks frozen source/protocol preflight, exact slot order/configs,
each raw file list, software, action/decision/reference/verifier/recovery/path,
injections, summaries, evaluation, manifest and terminal logs. It regenerates
the commissioning CSV exactly and reconstructs every pair from raw evidence.
The healthy-placement, native-injection and lower-semantic-divergence gates pass.
No V2R performance threshold is used.

The 12 Baseline/V1/V2-old trajectories also match the accepted M6 counterparts
exactly for all 9,600 steps: reset, actions, physical observations/contact,
reference, verifier, recovery, decisions, path and injections. This directly
checks preservation of the prior three systems in native execution.

Local replay uses Python 3.12.14, NumPy 2.3.5 and SciPy 1.17.0. One reconstructed
rotation diagnostic differs from the native report by `2.3623052299026615e-13`
rad. The auditor allows at most `1e-12` rad only for that derived diagnostic;
all other comparison fields, raw physical/controller/verifier values and gate
booleans remain exact. This does not change the native action tolerance,
physical equality contract or readiness threshold. Native fresh entry performs
its own exact report replay under the frozen native environment.

See [machine audit](evidence/AETHER_CL_M6R_Known16_Native_Audit.json) and
[reproducible read-only auditor](../../../tools/m6r_commission_archive_audit.py).
Given an extraction containing `m6r-commission`, run:

```bash
python tools/m6r_commission_archive_audit.py \
  --root /path/to/m6r-commission \
  --archive /path/to/aether-cl-m6r-known-commission.tar.gz \
  --log /path/to/m6r-known-commission.log \
  --m6-root /path/to/retained-m6-placement \
  --output /path/to/new-audit.json
```

## Native development outcomes

| Condition | Baseline | V1 | V2-old | V2R |
| --- | ---: | ---: | ---: | ---: |
| Normal | 2/2 | 2/2 | 2/2 | 2/2 |
| 8 cm post-release shift | 0/2 | 0/2 | 0/2 | 2/2 |

Normal old/repaired pairs have identical full 800-step trajectories and no retry.
At 8 cm both trigger at 342 and start one retry at 343. Their actions, physical
state/contact, reference, verifier and recovery are exact until the authorized
post-observation lower transition. The boundary observation and action remain
common; only the lower readiness decision differs.

| Boundary / subsequent behavior | Seed 100 | Seed 101 |
| --- | ---: | ---: |
| First lower-state divergence | 446 | 447 |
| TCP distance at common boundary | 15.297 mm | 10.625 mm |
| TCP vertical residual at boundary | 15.113 mm | 10.506 mm |
| Goal XY error at boundary | 3.242 mm | 1.885 mm |
| V2R first release action | 447 | 448 |
| V2R first retraction action | 457 | 458 |
| V2R first task success | 477 | 478 |
| V2R final XY error | 2.757 mm | 1.713 mm |

On both boundary states, minimum-motion/distance/orientation gates pass,
geometric support is true and XY lies within 25 mm. The old 3 mm Z condition
fails. V2R executes release and retraction, completes its single attempt with
141 retry actions and has released/supported/stable/retracted final task success.
V2-old executes 123 retry actions, times out after 40 lower actions, never executes
recovery release or retraction, and finishes held despite small final XY error.
Both failed old outcomes stay retained.

## Next boundary

Keep the server detached at the measurement revision above; no new bundle or
checkout is required for this documentation-only audit. Launch the
[single-parent fresh script](../../../aura-sim/prototype_aether_cl/scripts/run_m6r_fresh.sh)
with that exact SHA. It validates known16 again, rejects any previously recorded
reset of seeds 120–139, runs and retains first24, checks its evidence/viability
gate, copies its immutable pilot archive, then starts only the remaining 456.

No controller tuning, thresholds, durations, settings, seeds or measurement
sources changed after these observations. Fresh outcomes and independent audit
must return to 02 before further scope. Prototype A stays open; PR #1 stays
draft/unmerged and main unchanged. The two development rescues do not establish
fresh-seed generalization.
