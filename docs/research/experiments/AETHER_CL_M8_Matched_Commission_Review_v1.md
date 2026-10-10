# M8 matched force commissioning review

The 36-run matched development batch passes independent audit. It demonstrates
that the accepted effect-aligned placement recovery can repair the commissioned
engine-force failures on two reused development scenes. It does not establish
fresh-scene robustness. The next step is the frozen M8 study, beginning with a
retained first 18 execution and integrity-review pause.

Native measurement: `a910a8cab8b0f0f67daeb0178f44457383aab814`.
Archive: `aether-cl-m8-matched-commission-v1.tar.gz`, 19,863,433 bytes,
SHA-256 `f8a05548c08e08a8b93f60dca2a29a14f919abf7e34e379fbe12ac256e2c165c`.
The [machine review](evidence/AETHER_CL_M8_Matched_Commission_Review_v1.json)
has SHA-256 `4b9d0e9f83d050e1b5c22d69f7f48e5801636cb132e25c0afc38c05ed3b73577`.

| Commanded +Y force (N) | Baseline | V1 | V2 |
| --- | --- | --- | --- |
| 0 | 2/2 | 2/2 | 2/2 |
| 0.41868388652801514 | 2/2 | 2/2 | 2/2 |
| 1.857688546180725 | 0/2 | 0/2 | 2/2 |
| 2.322110652923584 | 1/2 | 1/2 | 2/2 |
| 2.9026384353637695 | 0/2 | 0/2 | 2/2 |
| 3.628298044204712 | 0/2 | 0/2 | 2/2 |

Baseline and V1 succeed in 5/12 scene-condition pairs; V2 succeeds in 12/12.
All seven failed matched cases invoke one episode and recover. There are zero
unnecessary attempts or final regressions among the five Baseline-success
pairs. These are seven scene-condition rescues on two scenes, not seven
independent scenes. All failed reference and verifier onsets occur at action 342;
first recovery actions occur at 343. Successful episodes use 125–199 recovery
actions and complete the effect-aligned lower transition, release, retraction
and final stable supported placement.

The nonmonotonic force response remains retained: seed 101 succeeds at 2.322111 N
with 24.305 mm final error and receives no recovery, while it fails at 1.857689 N.
The force grid is not filtered or reordered according to task outcome. Force
input is monotonic; contact-mediated displacement and success need not be.
Commands are five additive native force calls at action 296, with no immediate
cube pose or velocity write. Retracting finger contact remains part of the
native contact response.

All 412 indexed files have a complete, unique, safe archive file set and matching
sizes/hashes. Fifteen executed source/receipt snapshots match their measurement
Git blobs. Every parent/child identity, result and all 36 log start/end slots
match the fixed plan. All 28,800 actions, decisions, scorer/verifier states,
recovery states, path costs, summaries and verification metrics reconstruct
exactly. All 144,000 external physics samples, 150 force calls and 36 active
controller-gate audits regenerate exactly. Every retained native/physics/gate
audit JSON agrees with independent reconstruction.

All 34 matched comparisons pass: twelve full passive pairs, twelve recovery
common-prefix/full healthy pairs, and ten pre-force Baseline controls. The
twelve Baseline references also match the earlier dose batch across all 800
physical control records and 4,000 physics samples per case. All twelve paired
outcome rows regenerate. No initial-goal exclusion or missed force precondition
occurs in this development batch.

Replay used isolated Python 3.10.21 with NumPy 1.26.4 and SciPy 1.10.1; the native
server uses Python 3.10.22 with those same NumPy/SciPy versions. The first local
attempt used Python 3.12.14/NumPy 2.3.5/SciPy 1.17.0 and encountered a 6.28318548 raw
Euler-action representation difference for one V2 trajectory. The correctly
versioned arithmetic environment reproduces all 36 action streams with zero
error. No evidence, controller, scorer, pair requirement or replay tolerance
was changed to accommodate that difference. This pure audit does not reproduce
or claim to run the simulator locally.

The [fresh preregistration](AETHER_CL_M8_Placement_Preregistration.md) freezes
the same six forces and commissioned physics/controller mechanics. Authority
remains 02's DEC-0007 at `4d477da2a583717b773b3a1c746996a3c2127e40` for M8 only.
This engineering development review does not claim 02 acceptance of M8. No
fresh M8 outcome or model training exists at publication; first 18 is the next
native command, followed by independent review before 342 unstarted slots.
