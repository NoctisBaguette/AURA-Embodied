# M8 higher-dose response review and matched commissioning

The second force-response batch passes independent audit and provides placement
failures on both retained development scenes. The next step is matched
Baseline/V1/V2 commissioning on those same two seeds. Fresh M8 evaluation and
model training have not started. This engineering review does not constitute
02 acceptance of M8.

Authority remains DEC-0007 at `4d477da2a583717b773b3a1c746996a3c2127e40`:
physics-propagated placement disturbance, accepted M6R task/scorer/verifier and
effect-aligned recovery, privileged state, one bounded recovery episode, and
return to02 after frozen native evidence. No gripper, motion, threshold,
support or material redesign is introduced.

## Evidence and independent checks

The native batch ran at clean revision
`155283683148218bc5a45ecf2167585223650724`. The returned archive
`aether-cl-m8-force-commission-v2.tar.gz` is10,660,576 bytes with SHA-256
`7374077d443ffc3e93134af2fd3b4daca307c8664004df194c42fe2e905cded0`.
All226 indexed payload files verify; archive paths, types, uniqueness and the
complete payload set pass. All24 child results, parent identities and log
start/end slots match the fixed development plan. All13 source/receipt snapshots
match the measurement revision's Git blobs, including all eight accepted
placement files. Installed source, native binary, asset and package identities
remain unchanged.

Every trial replay regenerates its retained JSON exactly:19,200 controller
actions with zero maximum replay error, all decisions, independent endpoints,
verifier/recovery state, path, episode summary and terminal result. The22
instrumented runs contribute88,000 complete external100 Hz physics samples and
90 force calls. World+Y input, zero torque, force mode, action296/five-substep
window, support/release preconditions, immediate force-call pose/velocity
equality, continuity and control/physics endpoints all verify. There are no
initial-goal exclusions or missed application preconditions in this batch.

All22 comparisons regenerate: two full zero-force/no-hook controls, twelve
pre-force prefixes through action295 and eight repeats. Each repeat's complete
physical-sidecar bytes match. Six additional v1/v2 cross-batch reference checks
(normal/easy/previous-high on each seed) match all800 physical control records
and all4,000 external physics samples per run, despite the new Git revision and
development labels. Repeats and cross-batch checks reuse two scenes; they do not
increase the number of independent scenes.

Independent replay used Python3.12.14, NumPy2.3.5 and SciPy1.17.0 and reproduced
the native Python3.10.22/NumPy1.26.4/SciPy1.10.1 records exactly. No tolerance was
relaxed. The [machine receipt](evidence/AETHER_CL_M8_Force_Response_Review_v2.json)
retains all24 outcomes, physical effects, source identities, comparison results
and representative contact samples.

Legacy M6R `disturbance="none"` and `disturbance_applied=false` describe the
disabled synthetic relocation branch. Primary M8 records separately retain
the physical force commands and effects. The historical cube relocation and
velocity-reset function never executes.

## Measured main outcomes

Each nonzero input is applied for five100 Hz engine steps, approximately50 ms.
Final error is object-goal XY error, with the unchanged25 mm endpoint tolerance
and acquisition, release, designated support, retraction and stability criteria.

| World +Y force (N) | Seed100 final XY error (mm) | Seed101 final XY error (mm) | Baseline success |
| ---: | ---: | ---: | ---: |
| 0 | 0.263 | 0.244 | 2/2 |
| 0.418684 | 10.240 | 9.925 | 2/2 |
| 1.486151 | 39.811 | 21.805 | 1/2 |
| 1.857689 | 67.319 | 32.804 | 0/2 |
| 2.322111 | 83.912 | 24.305 | 1/2 |
| 2.902638 | 163.612 | 42.760 | 0/2 |
| 3.628298 | 215.754 | 113.361 | 0/2 |

Increasing force does not guarantee increasing final displacement in this
contact-constrained setting. Seed101 fails at1.857689 N and succeeds at2.322111 N.
The archived contact samples show different pulse/contact trajectories. At the
smaller dose, its world-Y velocity is+0.782756 m/s at action296/substep3, then
−0.184414 m/s at substep4 with finger2 Y contact force−7.883555 N. At the larger
dose, Y velocity reaches+1.000454 m/s at substep3; finger2 contacts continue
through substeps4/5 and the following action. These observations support a
contact-dependent response; an isolated friction-only drift model is insufficient.
Commanded force and measured displacement must remain distinct quantities.

All nominal controllers complete, including failed placements. This batch
establishes a reproducible physical failure range in these two development
scenes, not a broad robustness claim or a recovery result.

## Fixed matched development matrix

Keep normal/easy references and the entire previously declared four-point
geometric probe grid:0/0.418683887/1.857688546/2.322110653/2.902638435/3.628298044 N.
The old1.486151 N reference served as a reproducibility bridge between dose
batches. Keeping all four geometric probes preserves the nonmonotonic probe2
healthy outcome; selection does not filter points to manufacture a monotonic
success curve. This is a development family, not a fresh-study freeze.

`aether_cl.m8_matched` has a fixed36-run plan: seeds100/101, six inputs and three
systems. Baseline uses unchanged fixed placement; V1 adds unchanged passive
verification; V2 uses unchanged verification plus accepted M6R
`EffectAlignedRecovery` (formerly V2R), at most one400-action episode within
800 total actions. No V2-old/V3 comparator is present. Primary M8 names map to
the unchanged legacy runner's baseline/v1/v2r names in manifests.

The original accepted runner remains the sole source of motor commands. An
independent online reconstruction uses the same frozen controller/verifier
classes solely to determine the active phase for force instrumentation. It
must reconstruct each supplied action exactly before native stepping and must
match all retained decisions, verdicts and recovery snapshots afterward. It
never forwards its reconstructed action or feeds a score into motor control.
This prevents an early recovery phase at action296 from being mistaken for the
nominal retract phase. Such a case retains its missed application; there is no
retiming, second disturbance, fallback or additional recovery episode.

The unchanged force adapter validates the installed body/binding/hooks. Exact
inspection, v1 review and v2 review receipts plus clean source/native identity
are checked before native construction. Fifteen source/receipt snapshots are
retained. Every child regenerates the accepted action/scorer/verifier/recovery
audit, physical-force audit and a separate active-controller-gate audit.
Thirty-four matched comparisons cover twelve full passive pairs, twelve exact
recovery prefixes (or full traces without intervention) and ten Baseline
pre-force controls. Full physics samples also match throughout each compared
prefix. Paired summaries distinguish rescues, successful recovery episodes,
unnecessary attempts, regressions, detection, release/retraction progress and
added TCP travel. All native episode endpoints/costs and failure diagnoses remain
retained, including excluded, failed and non-applied outcomes.

Validation comprises29 force/refinement/matched fixtures plus eleven inspection
guards. The eleven new matched tests cover exact authoritative-action forwarding,
pre-step mismatch rejection, full800-action passive/control/recovery replays,
actual recovery-phase gating at296, late budget-rejected invocation prefixes,
tampered decisions/physics, initial-goal
zero-action exclusion, immutable receipt guards, all36 planned children and34
comparisons,15 indexed snapshots, timeout/partial retention and paired outcome
classification. Fixture endpoint perturbations are test mechanisms only, not
native physics evidence. Python3.10 syntax and CLI checks pass. The eight
accepted placement files and all earlier source/evidence files are unchanged.

Deployment uses a new offline Git bundle and new
`m8-matched-commission-v1` output/log/archive paths over port2221. The server
does not fetch GitHub. Detached execution prints `M8_MATCHED_COMMISSION_VALID`
only after the final archive is closed and every audit/comparison passes;
performance is not a commissioning pass condition. Failed/stopped/partial
evidence is archived and cannot be resumed or overwritten by this entry.

Return the matched archive for independent review before final M8
preregistration and fresh execution. Seeds160–179 remain reserved and require
a new retained-history check before entry. No fresh seed, model training,
RGB/RGB-D verification, memory/world model, Prototype B/C/D, foundation-model
integration, rendering or02W is started. Return to02 after frozen native M8
evidence and independent audit.
