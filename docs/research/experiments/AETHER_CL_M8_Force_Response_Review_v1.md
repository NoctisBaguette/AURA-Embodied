# M8 first physical-force response review and next development batch

The first known-seed force-response batch completed at clean native revision
`b6b01b863c89190dc795155877d38816216e6df6`. Its engine-force path passes
independent replay and reproducibility checks. Its friction-only drift estimates
overpredict displacement because the released cube can collide with the
retracting gripper. The next engineering step is a higher-dose development batch
on the same seeds and at the same boundary, before matched Baseline/V1/V2
commissioning or any final fresh M8 freeze.

This remains within02's DEC-0007 authority at
`4d477da2a583717b773b3a1c746996a3c2127e40`: physical force/impulse disturbance,
accepted M6R placement endpoint and recovery, privileged verification, one
bounded recovery episode, no motion/tolerance redesign. No fresh evaluation or
model training occurred. No02 acceptance of M8 is implied by this development
review.

## Retained evidence and independent audit

The returned `aether-cl-m8-force-commission-v1.tar.gz` is8,843,029 bytes,
SHA-256 `309a191f5683f832f1e5a2e338886fcd8c73d9d3c83416ec87a5e58e432da815`.
All188 indexed files verify, archive names are unique and no unexpected payload
or path traversal exists. All20 child results and native identities agree with
the parent. All20 log start/end pairs agree with the fixed plan and every child
returned zero. Eight accepted placement sources, two original force-study
sources and the installed-inspection receipt match their eleven source
snapshots byte-for-byte and the published measurement revision.

All20 native trials reconstruct exactly:16,000 controller actions with zero
maximum action error, every decision, independent task endpoint, path, summary
and result. All18 instrumented physical traces regenerate exactly:72,000
external100 Hz samples,70 executed force calls, fixed action296/five-substep
window, recorded release/support preconditions, world+Y force, zero torque and
force mode. Immediate force-call pose/velocity equality, inter-step continuity
and control/physics endpoint equality all pass. There are no missed force
preconditions or initial-goal exclusions in this development batch.

All18 exact comparisons regenerate: two full zero-force/no-hook pairs, ten
pre-force prefixes through action295 and six complete repeated trials. The
repeated physics-sidecar bytes also match exactly. Zero-force instrumentation
does not alter any recorded native action or state. Independent replay used
Python3.12.14/NumPy2.3.5/SciPy1.17.0 and reproduced the native
Python3.10.22/NumPy1.26.4/SciPy1.10.1 records exactly; no tolerance was changed.
The [machine review receipt](evidence/AETHER_CL_M8_Force_Response_Review_v1.json)
retains source/native identities, every audit check, all20 outcomes, pulse states,
contact evidence and the next dose rule.

The legacy M6R `disturbance="none"` and `disturbance_applied=false` fields refer
only to the disabled synthetic relocation branch. Primary M8 carriers and
physics sidecars correctly record all70 physical force calls. Source inspection
and the fixed configuration verify that the historical cube-pose/velocity
relocation function never executes. Task initialization's accepted goal-site
projection remains unchanged.

## Actual response, not the drift labels

These are the twelve main Baseline development episodes; originals and repeats
are controls rather than extra independent scenes. Final error is measured
against the placement goal. The independent endpoint retains its25 mm XY
tolerance and historical acquisition/release/support/clearance/stability rules.

| Force +Y (N),50 ms | Original estimated drift label | Seed100 final XY error (mm) | Seed101 final XY error (mm) | Baseline final success |
| ---: | ---: | ---: | ---: | ---: |
| 0 | normal | 0.263 | 0.244 | 2/2 |
| 0.418684 | 10 mm | 10.240 | 9.925 | 2/2 |
| 0.722359 | 40 mm | 21.104 | 20.793 | 2/2 |
| 0.977555 | 80 mm | 21.492 | 16.538 | 2/2 |
| 1.174039 | 120 mm | 41.582 | 18.442 | 1/2 |
| 1.486151 | 200 mm | 39.811 | 21.805 | 1/2 |

The10 mm estimate is close to its actual10.017/10.112 mm displacement from the
pulse start and has no sampled post-pulse finger contact. Every nonzero main
dose above it has contact with finger2 during or soon after the force pulse.
For example, at1.174039 N on seed101, the cube's Y velocity grows to
`+0.616308689 m/s` at action296/substep4. On substep5, finger2 applies
`-5.748970032 N` along world Y and the cube's Y velocity becomes
`-0.127120450 m/s`, despite the continuing positive force input. This observed
contact and velocity reversal explain why an isolated sliding model is
insufficient here. Actual response varies with scene/grasp geometry and need
not be monotonic even when commanded force is monotonic.

The120/200 mm labels therefore must not be reported as actual disturbances of
those sizes. Baseline's two main failures are seed100 outcomes at the two largest
forces; the repeat of its largest-force failure is the same scene/dose, not a
third independent failure. All20 nominal controllers complete their schedule,
including those failed placements. Force application and final task success
remain distinct outcomes. Sampled table-force drops are retained as contact
diagnostics and must not be conflated with a sustained unsupported endpoint.

This establishes a usable, reproducible engine-force mechanism in these two
development scenes. It does not yet establish a broad robustness family or
verification/recovery performance under physical disturbances.

## Fixed24 next development plan

Keep world+Y net force, zero torque, `mode="force"`, action296 and its five
100 Hz substeps. Keep the same release/support precondition, accepted motion,
reset, scorer,800-action budget and seeds100/101. Missed preconditions remain
non-applied outcomes without retiming. No cube state write, gripper change,
support/friction change or new disturbance mechanism is introduced.

Use the verified zero/easy reference and previous maximum, then four probes
`F_k = float32(F_max * 1.25^k)`, k=1–4, with
`F_max = 1.486150860786438 N` from the audited v1 batch. This bounded geometric
grid extends the measured input range without assuming a displacement or
adapting to fresh outcomes. Its nominal50 ms command integral ranges up to
approximately0.1814 N·s. All point labels now identify force inputs; no drift
target is supplied.

| Point | Exact float32 force +Y (N) | Use |
| --- | ---: | --- |
| normal | 0 | No force call |
| force-easy-v1 | 0.41868388652801514 | Verified easy reference |
| force-reference-v1-high | 1.486150860786438 | Highest previous input |
| force-probe-1 | 1.857688546180725 | 1.25× previous maximum |
| force-probe-2 | 2.322110652923584 | 1.25²× previous maximum |
| force-probe-3 | 2.9026384353637695 | 1.25³× previous maximum |
| force-probe-4 | 3.628298044204712 | 1.25⁴× previous maximum |

The24 isolated interpreters comprise two original no-hook normal runs, fourteen
main runs (seven inputs × two seeds), and eight repeats (normal, previous
maximum, probe2 and probe4 × two seeds). Twenty-two exact comparisons cover
two zero-force/no-hook controls, twelve pre-force prefixes and eight full
reproducibility pairs, including identical physics-sidecar bytes. Failure,
exclusion and non-application are retained without a performance success gate.

The new `aether_cl.m8_force_refine` entry reuses the unchanged native force
adapter, physical auditor, pair comparator, archive writer and accepted M6R
runner. Its primary manifests retain the legacy-carrier explanation. It
requires the exact reviewed v1 receipt, installed identities and clean pinned
Git before native construction. The eleven prior source/receipt bytes and all
existing Git files remain unchanged; new source and both receipts are included
in the returned evidence. Existing output/archive/log paths are not overwritten.
A receipt guard failure produces indexed retained error evidence before any
native construction or child; a caught child error/timeout retains the started
slot and partial files, stops and gets no replacement.

## Execution and next boundary

Use the new pinned offline Git bundle through the established
`jiangle@166.111.59.11`, port2221, and existing `aether-cl` environment. Preserve
the v1 output, archive, log and bundle. From the prototype directory:

```bash
python -u -m aether_cl.m8_force_refine \
  --expected-head EXACT_REFINEMENT_COMMIT \
  --output runs/m8-force-commission-v2 \
  --archive /home/jiangle/aura-work/aether-cl-m8-force-commission-v2.tar.gz
```

The supplied launch uses `nohup` and
`/home/jiangle/aura-work/m8-force-commission-v2.log`. Native progress prints
START/END1–24; `M8_FORCE_REFINEMENT_VALID` appears only after a complete archive
has been written. Return archive/log even on a retained error. This marker
validates development evidence and does not select a final family or authorize
fresh execution. The entry point has no fresh or matched-system mode.

Six new focused tests cover the fixed24 plan, geometric dose construction,
review-receipt rejection before native access with error retention, all24 child
launches/22 comparisons and both indexed receipts, failed-child retention without
replacement, and absence of a new cube setter/force API. All eighteen force
tests and eleven inspection guards pass locally; Python3.10 syntax and CLI help
pass. These tests do not validate the new high-dose native response, which is
pending. After its independent review, prepare matched Baseline/V1/V2 with the
accepted M6R V2R recovery, then freeze the complete study before fresh160–179
only if the fresh-entry history guard passes. Return to02 after frozen native
M8 evidence and independent audit. RGB/RGB-D, memory/world models, Prototype
B/C/D, foundation-model integration, rendering and02W remain outside this batch.
