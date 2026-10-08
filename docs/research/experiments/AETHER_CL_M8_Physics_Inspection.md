# AETHER-CL M8 — Installed Physics Interface Inspection

Date: 2026-10-08 (UTC).

Status: development inspection prepared; installed binding response, force
commissioning and native M8 outcomes are pending. This is not a frozen M8
measurement protocol or a result publication.

Authority: [02's M7 acceptance and M8 scope](AETHER_CL_M7_02_Research_Review_v0.1.md),
DEC-0007 at `4d477da2a583717b773b3a1c746996a3c2127e40`.
M7's measurement and evidence remain unchanged. PR #1 remains open, draft and
unmerged; main remains `901ed3bb46522ffc22b3ec6311c22287cb1984bc`.

## Authorized scientific change

Return to the accepted M6R released-placement task. Compare Baseline, passive V1
and V2 using the accepted M6R `EffectAlignedRecovery` behavior. Preserve nominal
motion, the independent release/support/goal/clearance/stability endpoint,
25 mm XY tolerance, one bounded recovery episode and the 800-action budget.
M6 V2-old is not part of the M8 matrix.

M6/M6R's historical injection at action296 calls `shift_native`, which relocates
the cube and zeroes velocities. M8 must not call that disturbance path. It needs
a separate adapter/runner using the installed engine's physical force/impulse
API. The existing goal-site Z projection is task setup, not a disturbance, and
does not authorize cube pose or velocity mutation during M8.

No existing M0–M7 implementation or protocol is changed by this inspection.

## Why inspect before commissioning

02 deliberately did not specify arbitrary Newton or Newton-second values.
Choosing the supported API, force application window and development magnitudes
requires exact installed-binding and geometry evidence. Upstream examples alone
do not establish what the native SAPIEN3.0.3 / ManiSkill3.0.1 installation does.

[`tools/m8_physics_inspection.py`](../../../tools/m8_physics_inspection.py)
collects that evidence with these boundaries:

- Require the requested clean Git head descending from DEC-0007, Python3.10 and
  the unchanged native package versions and installed sources recorded for M7.
- Hash-check eight accepted placement/controller/verifier/recovery sources.
- Scan every retained `events.jsonl` for native reset seeds, including failed
  and stopped runs. Report preferred160–179 overlap and an unused contiguous
  range as provenance only; this does not freeze or execute a fresh selection.
- Require retained proof that development seed100 was already observed.
- Capture relevant installed ManiSkill sources, SAPIEN interface stubs,
  public binding descriptors/docstrings and native-library hashes.
- Construct one unrendered CPU `PickCube-v1` and explicitly reset only seed100.
  Before construction, inspect the pinned `BaseEnv.__init__` seed expression.
  Permit only known100/2022 initialization; the standard
  `[2022 + i for i in range(self.num_envs)]` expression also yields only2022
  because the unchanged builder fixes `num_envs=1`. Unresolved or fresh
  initialization seeds stop execution before environment creation.
- Read actual cube rigid-body mass/inertia/damping, collision materials,
  friction, table geometry/support contact, physics frequency/system and the
  actual pre/post-physics hooks. Unsupported getters remain visible in the
  report instead of being filled with assumed values.
- Execute zero external controller actions, force/impulse commands or explicit
  cube pose/velocity writes. The native constructor/reset still performs its
  usual environment initialization; no training or fresh evaluation occurs.
  The inspection does not call M6's goal projection or synthetic disturbance.
- Retain report, executed inspection source and file index in a gzip tar archive,
  also on a caught error. Existing report/archive paths are never overwritten.

An inspection-ready status means the capture completed, not that a force API
has passed physical commissioning. Missing mass, friction or a suitable API must
be resolved from the captured evidence before implementing/executing a force
study. Reported contact/pose at native reset is diagnostic geometry, not a
placement success outcome or a released-cube force-response test.

## Native inspection

The server is offline, as in the retained M6R/M7 deployment procedure. Fetch
`06-01/aether-cl-m0` on the Windows laptop, verify the supplied inspection head,
create a full Git bundle of that remote-tracking ref, and transfer it with
`scp -P 2221` to `/home/jiangle/aura-work`. Fetch the bundle on the server and
detach at the supplied exact commit. Do not fetch GitHub from the offline server
or overwrite a previous bundle. The Windows checkout need not be switched or
modified to prepare the bundle.

On the existing server, activate the unchanged `aether-cl` environment, unset
`LD_PRELOAD`, use the established GLVND library directory and GPU visibility,
and switch a clean checkout to the published inspection revision. Invoke from
the repository root:

```bash
python -u tools/m8_physics_inspection.py \
  --expected-head "$(git rev-parse HEAD)" \
  --output /home/jiangle/aura-work/m8-physics-inspection-v1 \
  --archive /home/jiangle/aura-work/aether-cl-m8-physics-inspection-v1.tar.gz
```

Use the exact inspection commit in the supplied execution block rather than
following later branch movement. Do not run this inspection concurrently with
another native experiment. No session-ID override is needed. A shell block may
use `set -e` inside a child Bash process so a failed guard does not close the
interactive SSH connection.

Transfer uses the existing connection, `jiangle@166.111.59.11` on port2221:

```powershell
scp -P 2221 jiangle@166.111.59.11:/home/jiangle/aura-work/aether-cl-m8-physics-inspection-v1.tar.gz C:\Workspace\AURA-Deploy\
```

Return the archive even if its report retains an error. Do not install/upgrade
dependencies, alter installed assets or bypass a guard to obtain a ready status.

## Subsequent engineering gates

1. Independently review the returned installed sources/binding docs, live body
   properties and timing hooks. Choose an explicitly supported force/impulse
   interface without a hidden pose or velocity overwrite fallback.
2. Commission its physical response using only already-observed development
   seeds. Keep the accepted motion and scorer/recovery unchanged. Record the
   world-frame command, physical substep window, release/support precondition,
   actual displacement, velocities and contacts, including zero-force controls.
   Validate reproducibility and passive trace equality. Retain every failed,
   stopped or non-applied development attempt.
3. Select a monotonic normal/easy/multiple-harder family from measured mass,
   friction/support and API behavior. Freeze all sources, timing, duration,
   direction, family, scorer/verifier/recovery, matrix and history before fresh
   native outcomes. Precondition failures remain non-applied retained outcomes;
   there is no retiming or adaptive seed replacement.
4. Use fresh160–179 only if the fresh-entry history recheck passes. Preserve
   isolated interpreters, replay/hash guards, exact passive equality, recovery
   prefixes, independent endpoint reconstruction and explicit audit of the
   physical disturbance call path. Retain existing initial-in-goal exclusions
   under the unchanged M6R task definition, along with failed/aborted/missed
   episodes, rather than choosing replacement seeds.
5. After frozen M8 evidence and independent audit, return to02 before further
   scope. If the installed engine cannot provide a reproducible force/impulse
   mechanism without materially redesigning the environment, return to02
   before substituting a pusher, velocity overwrite or another mechanism.

RGB/RGB-D verification, memory/world models, Prototype B/C/D, foundation models,
motion optimization and02W are outside M8. Actual camera/arm rendering was
deferred by the user and is not part of this inspection.

## Local validation

Eight focused standard-library tests check retained-history collision handling,
unobserved/malformed seed rejection, constructor seed guards, descriptor-only
API inspection, the absence of external rollout/force/pose/velocity mutation
calls, and indexed retained error bundles without archive/report overwrite.
CLI help and Python3.10 syntax parse pass. Existing parent file bytes are checked
against Git blobs before publication. These checks do not validate native
simulator behavior; that boundary is the server inspection and later development
force commissioning.
