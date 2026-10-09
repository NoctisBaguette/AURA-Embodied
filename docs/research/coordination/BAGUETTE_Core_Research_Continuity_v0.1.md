# BAGUETTE Core Research Continuity v0.1

Date: 2026-10-09  
Status: **research coordination / continuity protocol**  
Public project identity: **AURA-Embodied / AURA**  
Historical architecture codename: **AETHER / AETHER-CL**  
Provisional internal successor/core codename: **BAGUETTE** (not yet a public or frozen architecture name)

## Purpose

This document exists to minimize research-context loss across long ChatGPT
conversations, Work-mode investigations, engineering branches and eventual chat
rollovers.

The persistent normal-chat architecture thread (currently branch/chat 02, planned
to be renamed **BAGUETTE**) is the intellectual core of AURA. Work-mode companion
02W supports deep investigations but does not replace the core thread or become
the final architecture authority.

Historical AETHER/AETHER-CL experiment names remain unchanged for provenance.

## 1. Core routing

```text
05 Frontier Watch
    ↓
durable GitHub frontier memory
    ↓
BAGUETTE Core / normal 02
    ↓
architecture interpretation + research decisions
    ├─ if bounded and clear → 06 / 06-xx engineering
    └─ if consequential / multi-paper / unresolved → 02W deep research
                                              ↓
                                      return synthesis to Core
                                              ↓
                                      Core final decision
                                              ↓
                                           06 implementation
                                              ↓
                                      evidence returns to Core
```

Other branches remain complementary:

- **00 / HQ** — project-level coordination, application/funding, team/resource and
  program decisions;
- **01 / 01W** — embodied-intelligence landscape, papers and broader synthesis;
- **05** — recurring frontier watch and competitive/prior-art signals;
- **06-HQ / 06-xx** — implementation, experiments and engineering;
- **07** — robot/physical-system integration;
- **08** — research outputs, documentation and communication.

## 2. Authority hierarchy

When information differs across chats, use durable records rather than chat memory.

### Project identity / current architecture

Primary:
- `ARCHITECTURE.md`
- `ROADMAP.md`
- `docs/research/architecture/aura/AURA_State_Transition_Architecture_v0.2.md`

### Frontier / external research

Primary on `main`:
- `docs/research/frontier_watch/CURRENT.md`
- `docs/research/frontier_watch/TREND_LEDGER.md`
- dated weekly files under `docs/research/frontier_watch/YYYY/`
- `RESEARCH_LOG.md`

05 supplies evidence and signals; it does not directly rewrite architecture
decisions without Core review.

### Experiment evidence

Primary on the active experiment branch until reconciliation:
- `06-01/aether-cl-m0`
- experiment reports under `docs/research/experiments/`
- evidence/audit artifacts;
- experiment-specific 02 reviews;
- the experiment branch's `DECISION_LOG.md`.

### Decision numbering warning

`main` and `06-01/aether-cl-m0` currently have diverged decision histories.
Do not create conflicting global DEC IDs until those histories are reconciled.

## 3. BAGUETTE naming status

**BAGUETTE is provisional.**

Current usage:
- convenient internal name for the persistent Core architecture/research thread;
- possible successor to the AETHER codename.

Not yet decided:
- whether BAGUETTE becomes the published architecture name;
- what BAGUETTE would expand to, if anything;
- whether a different final architecture name should be selected.

Public materials should continue to use **AURA**, **AURA architecture**, or
**AURA adaptive manipulation-intelligence system** unless HQ/Core later freezes
a new public architecture name.

Do not rename historical AETHER/AETHER-CL files or experiment identifiers.

## 4. What belongs in the Core thread

The Core thread maintains:

- project architecture and architecture evolution;
- distinction among decisions, hypotheses and candidate ideas;
- interpretation of experiment results;
- selection of the next discriminating experiment;
- integration of 05 Frontier Watch findings;
- routing into 02W when deep investigation is needed;
- routing into 06 when implementation is justified;
- cross-branch consistency;
- research limits and unsupported claims;
- naming/identity implications that affect architecture communication.

The Core thread should challenge assumptions rather than defend previous diagrams.

## 5. What belongs in 02W

02W is used only when the problem becomes consequential enough to benefit from
Work-mode depth, for example:

- non-privileged task-state / transition-verification architecture;
- competing memory architectures;
- explicit vs latent task-state design;
- hierarchical/minimum-change recovery design;
- embodiment-transfer interfaces;
- substantial architecture comparison against systems such as DynaHarness,
  HELM, CRIS-0, Long-WAM or VPP2;
- benchmark/evaluation design when broad prior-art review is required.

02W returns evidence, alternatives, risks and a recommendation to Core. Core then
decides what becomes a project decision or 06 experiment.

## 6. Required durable checkpoints

Update GitHub at these moments:

1. **after each accepted 06 experiment return** — record evidence-backed findings,
   limitations and the next research decision;
2. **after each 02W investigation** — record the synthesis and Core decision;
3. **after material 05 Frontier Watch updates** — review implications in Core and
   record only architecture-relevant changes;
4. **after major HQ/application-derived reframing** — classify project decisions
   vs hypotheses before updating architecture;
5. **before a long Core or 02W chat is near rollover/max length** — create a
   dedicated continuity checkpoint;
6. **after naming/scope changes** — preserve why the decision changed.

Do not commit every brainstorm. Durable memory should preserve conclusions,
evidence, unresolved questions and reasoning.

## 7. Chat rollover protocol

Before a Core or 02W conversation is transferred to a new chat, create or update
a continuity checkpoint containing:

- current architecture version and public/internal naming status;
- frozen project decisions;
- evidence-backed experimental findings;
- active working hypotheses;
- rejected/weakened hypotheses;
- open architecture questions;
- latest 05 Frontier Watch implications;
- latest accepted 06 milestone and exact branch/head;
- current 02W status and output, if any;
- pending engineering handoff, if any;
- current branch divergence/reconciliation state;
- exact files the successor chat should read first.

The successor chat should **read GitHub first**, not rely on a giant copied chat
transcript.

Recommended successor startup order:

1. this continuity file;
2. `ARCHITECTURE.md`;
3. current architecture checkpoint under `docs/research/architecture/aura/`;
4. `ROADMAP.md`;
5. Frontier Watch `CURRENT.md` + latest weekly report;
6. latest experiment return + 02 review;
7. relevant decision log(s);
8. only then older history if needed.

## 8. Current architecture checkpoint

As of 2026-10-09:

- AURA public identity is frozen;
- AETHER is historical/internal and should not be promoted publicly;
- BAGUETTE is a provisional internal successor/core codename;
- physical picking/soft-grasping is an active integrated AURA branch;
- migration is a central evaluation principle but M0-M8 are not yet a formal
  migration experiment;
- task-relevant physical state transition is the current common analysis
  abstraction;
- planning feasibility and execution reliability are distinct;
- planning and verification should share compatible transition semantics;
- verification is selective and temporal;
- local recovery has a bounded corrective envelope;
- non-privileged verification remains the immediate Prototype-A architecture gap;
- current preferred experimental discipline is to isolate sensing realism first,
  then freeze the verifier and test an explicit transfer axis separately.

## 9. Immediate next route

Before creating the next Work-mode chat, Core should provide a sharpened 02W
mandate around:

> **minimum task-relevant state + intended transition representation +
> non-privileged state estimation/verification + uncertainty/temporal decision +
> M9 design**

The deep investigation should challenge whether M9 should remain a pure sensing
ablation (preferred for causal clarity) or combine a transfer axis.

No new 06 implementation is authorized until 02W returns and Core approves the
experiment.
