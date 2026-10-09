# AURA-Embodied Research Roadmap

## Identity

**AURA-Embodied** studies **Adaptive Robotic Manipulation Intelligence** for
generalizable physical agents.

Zero Point defines a one-year **Phase I** of a longer research program; it is not
the lifetime of AURA.

## Research center

Primary focus: object-centric upper-body manipulation intelligence.

AURA studies how robots maintain, verify, recover, transfer and improve
manipulation capability across:

- objects;
- tasks;
- environments;
- embodiments;
- experiences.

Navigation, SLAM, locomotion and lower-body control are not current primary
research targets.

## Two complementary research branches

### Physical branch

The continuing intelligent-picking / soft-grasping system is an active AURA
physical branch. It provides:

- existing engineering capability;
- real physical failure cases;
- perception/control/end-effector work;
- competition and repeated-evaluation opportunities;
- a validation environment for selected AURA mechanisms.

### Controlled research branch

Simulation and public manipulation tasks/benchmarks provide:

- controlled interventions;
- matched baselines;
- reproducibility;
- failure injection;
- architecture ablations;
- transfer tests before physical deployment.

The intended loop is physical problem -> controlled experiment -> architecture
update -> physical validation.

## Current Phase-I checkpoint

Completed or substantially established:

- embodied-intelligence landscape and weekly frontier monitoring;
- AURA/AETHER architecture evolution;
- AETHER-CL Prototype A through M8;
- verification-gating attribution;
- released placement and effect-aligned recovery;
- contact-rich insertion;
- physics-propagated disturbance evaluation;
- strict replay/audit infrastructure.

Immediate architecture gap:

- non-privileged RGB/RGB-D/proprioceptive verification.

## Fall semester

Priority work:

- continue the LingBot competition track as a finite VLA/model-engineering
  learning branch;
- continue substantial development of the picking/soft-grasping system;
- improve RGB + RGB-D perception, robot-arm control and end-effector reliability;
- finish the task-relevant state / transition-verification architecture
  checkpoint;
- design and begin non-privileged verification;
- define the first explicit transfer-oriented experiment;
- continue weekly Frontier Watch and architecture review.

The physical branch is not being "restored"; it is already developed and should
be advanced seriously.

## Winter break

Emphasize remote software/model/simulation work:

- reproduce/freeze a strong public baseline where tractable;
- implement one selected AURA mechanism;
- run matched baseline-vs-intervention experiments;
- test at least one explicit transfer axis;
- package interfaces and protocols for spring physical work;
- continue architecture/frontier research.

A useful structure is:

```text
Baseline
vs
Baseline + non-privileged verification
vs
Baseline + verification + bounded recovery
```

followed by a separate transfer study once the sensing interface is stable.

## Spring semester

- integrate validated software into the continuing physical picking system;
- continue end-effector/hardware development;
- improve repeated physical reliability;
- compare modular, learned/VLA and AURA-enhanced approaches;
- test migration across multiple objects/environments;
- add at least one second task/scenario family where feasible;
- connect simulation findings to selected real-robot validation;
- evolve architecture from the current v0.2 checkpoint using evidence;
- pursue aligned competitions when they advance the research.

## Late spring / early summer Phase-I target

A strong checkpoint should include:

- substantially improved physical picking system;
- one or more learned-policy/VLA baselines evaluated;
- at least one selected AURA mechanism validated under non-privileged sensing;
- explicit migration evidence across several objects/environments and at least
  two task/scenario families where feasible;
- simulation and physical evidence connected;
- baseline comparisons with retained failure analysis;
- updated architecture and clear Phase-II research questions.

Stretch goals include:

- real-robot learned/VLA policy;
- end-effector transfer;
- simulation-to-real transfer;
- persistent experience memory;
- WAM-assisted action ranking/verification;
- dual-arm adaptation;
- publication-quality architecture ablations.

## Evaluation strategy

Use public task/benchmark infrastructure when possible, then add controlled AURA
conditions such as:

- unseen objects;
- changed layouts;
- disturbances;
- sensing uncertainty;
- verification ambiguity;
- local recovery opportunities;
- failure injection;
- task transfer;
- latency accounting.

Do not promise a universal benchmark during Phase I.

## Research loop

```text
frontier / physical observation
    ↓
explicit hypothesis
    ↓
controlled implementation
    ↓
matched experiment
    ↓
failure analysis
    ↓
architecture decision
    ↓
physical / transfer validation
```

AURA does not wait for a final architecture before experimenting, and it does not
promote new mechanisms without evidence.
