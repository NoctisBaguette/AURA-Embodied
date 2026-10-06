# AETHER-CL M5 — Return to 02

Date: 2026-10-06 (Asia/Shanghai)

Historical handoff: subsequently [accepted by 02](AETHER_CL_M5_02_Research_Review_v0.1.md)
under DEC-0004 at `03b9b2dc77c33dc1aa47edd67dcb20238ad8b0bb`.
The new active round is [M6 Support Placement and Release](AETHER_CL_M6_Placement.md),
with native evidence still pending. The original return and findings below are retained.

**M5's engineering round is complete: implementation, frozen native execution
and independent archive audit. Return to 02 now for research review before
further implementation. Prototype A is still scientifically open.**

Authority is [DEC-0003 and the 02 review](AETHER_CL_02_Research_Review_v0.1.md)
at `3c919ecca401a73fe04a676c019c33b8a85b440a`. M5 adds only the scheduled
same-capability V3 comparator. All prior scientific execution modules and
protocols stay unchanged; no motion tuning or next task was implemented.

## Native evidence

Fresh preregistered seeds 80–99; two six-point shift/drop families; four
systems; 960 eligible isolated trials, 48 cells and 345,600 actions. All
4,804 indexed hashes, controller/reference/verifier replay, 1,160 strict
comparisons and exact native aggregate JSON/CSV reproduction pass.
All 180 aligned-trigger V2/V3 pairs have identical full physical traces.
No field or strict comparison tolerance was waived; no failure was replaced.

Native implementation commit: `12a9d2626636206e1687fa24df507bbadbc2a37d`.
Archive: `aether-cl-m5-attribution-seeds80-99.tar.gz` (129,811,535 bytes).
SHA-256: `a14d7542fcff8f025f13c72fb209f9c13e8666af0d8571855e3ad7035f6bbcab`.

## Findings requiring 02 interpretation

| Question | M5 finding | Bounded interpretation |
| --- | --- | --- |
| Does gating avoid unnecessary work? | V2 makes zero attempts on all 60 baseline-success point/seed controls; V3 retries all 60 | Supports selective invocation value |
| Can ungated retry harm a healthy task? | Healthy drop-family control: V2 20/20, V3 0/20; 20 scheduled retries drop a valid grasp and abort | Avoiding harmful intervention is observed for this comparator |
| Does gating improve already aligned recovery? | All 180 failure cases have exact V2/V3 physical trace equality, equal cost and equal success (177/180) | No additional disturbed-task benefit is observed under these aligned schedules |
| Is performance uniformly perfect at 20 cm? | Shift 19/20; drop 18/20 in both recovery systems | Fresh seeds expose preserved controller limits |
| Does final success mean complete recovery phases? | Five drop attempts per system abort at the action deadline while final task succeeds | Keep completion and scoring separate |

Normal-shift and 2 cm shift V3 attempts retain 20/20 success but add means of
132.15/131.70 actions and 0.5479/0.5473 m TCP travel; final median goal error
also increases. Healthy drop V3 adds 71.70 actions/0.2338 m, fails all 20,
and never establishes a new grasp after reopening the valid one. V2 avoids
these unnecessary/harmful attempts. Denominators and all failed costs are
preserved in the [full report](AETHER_CL_M5_Attribution.md#audited-native-results).

Suggested H3 update for 02 review: support for verification as a selective
intervention gate in this held-cube scope; necessity for successful recovery
remains unestablished when a phase-aware verifier-free schedule already
invokes the same retry at the same time. This is 06's evidence interpretation,
not a unilateral edit to 02's hypothesis register. H4 remains bounded by the
shared recovery capability and measured failures.

The controller reads privileged simulator state; V3 is family/phase-aware
and retains local recovery feedback. This is an invocation-gating ablation,
not removal of all sensing/feedback or a deployable alternative policy.
Twenty common seeds are reused across points; these are not 960 independent
initial scenes. No camera verification, physical-force disturbance,
release/support placement or contact-rich insertion was demonstrated.

## GitHub state and inspectable artifacts

Repository: [NoctisBaguette/AURA-Embodied](https://github.com/NoctisBaguette/AURA-Embodied).
Branch: `06-01/aether-cl-m0`.
[PR #1](https://github.com/NoctisBaguette/AURA-Embodied/pull/1) remains open,
draft and unmerged. Main is unchanged. Native evidence was generated at the
implementation commit above; the result publication is a subsequent
documentation/evidence-only commit, not a new executed controller revision.

- [M5 protocol and results](AETHER_CL_M5_Attribution.md).
- [Frozen protocol JSON](evidence/AETHER_CL_M5_Attribution_Protocol.json).
- [Independent native audit and complete episode table](evidence/AETHER_CL_M5_Native_Audit.json).
- [Separate paused live demonstration commands](AETHER_CL_M5_Live_Demonstrations.md).
- [Earlier M0–M4 handoff](AETHER_CL_06_01_Return_to_02.md), retained historically.
- Root experiment log/readmes and PR description reflect this return.

The uploaded raw archive is external evidence, identified by the exact hash;
it is not stored as a 124 MB binary in Git. Live demonstrations are optional
new runs and do not change or replace the archive or its conclusions.

## Required next decision

02 should review whether this bounded causal attribution satisfies M5, update
H3/H4 claims, and define the next frozen engineering scope. The outstanding
Prototype A closure dimensions remain support placement/release, contact-rich
insertion, at least one physics-propagated disturbance and at least one
non-privileged sensor verifier. Their order and protocol remain 02 decisions.

**Do not automatically start those tasks, optimize motion, or activate
Prototype B/C/D, memory, world models or 02W from this handoff.**
