# AURA-Embodied Frontier Watch

This directory is the durable research memory for **05 — Frontier Watch**.

Its role is narrower than the companion Embodied-AI Research frontier watch. The Embodied-AI project scans embodied AI broadly; AURA uses that scan as one input, performs an independent scan, and then applies an AURA-specific filter focused on **adaptive robotic manipulation intelligence**.

## Purpose

Track meaningful developments in:

- VLA / VLM systems for manipulation;
- long-horizon task intelligence;
- task state and memory;
- world models used for physical decision making;
- verification, failure diagnosis, recovery, and learning;
- embodiment transfer and adaptation;
- manipulation-specific perception and physical interaction;
- datasets, benchmarks, simulators, and evaluation methods;
- major lab/company/open-source releases with technical relevance.

This is not a raw news feed.

## Relationship to Embodied-AI Research

Primary upstream companion:

- https://github.com/NoctisBaguette/Embodied-AI-Research/tree/main/reports/frontier_watch

The intended weekly workflow is:

```
Monday: Embodied-AI broad frontier scan
        ↓
Thursday: AURA reads the Embodied-AI report
          + performs an independent scan
          + applies the manipulation/AETHER filter
          ↓
AURA research and experiment implications
```

AURA should explicitly distinguish:

- **CONFIRMED** — independently supports a signal already found upstream;
- **NEW** — relevant development found by AURA but not emphasized upstream;
- **DIFFERENT INTERPRETATION** — same evidence, different AURA conclusion;
- **NO ACTION** — interesting broadly, but not worth AURA time now.

## Decision vocabulary

- **WATCH**
- **READ**
- **DEEP DIVE**
- **REPRODUCE**
- **NO ACTION**

These are research-priority decisions, not paper-quality scores.

## Architecture-change rule

Frontier Watch does **not** directly rewrite `ARCHITECTURE.md` or `DECISION_LOG.md` because a new paper appeared.

Instead:

```
05 Frontier Watch
    ↓
frontier_watch research memory
    ↓
02 architecture review
    ↓
ARCHITECTURE.md / DECISION_LOG.md if justified
    ↓
06 experiments / implementation
    ↓
EXPERIMENT_LOG.md
```

This keeps AETHER evidence-driven rather than trend-driven.

## Execution protection — 2026-10-19

User direction: stay aware of the frontier while continuing to develop, test, and improve. Repeatedly revising the research direction is not a substitute for implementation.

**Awareness can change weekly; an approved experiment does not automatically change weekly.**

Read AURA's current `ROADMAP.md`, the Core continuity record, and the latest applicable engineering acceptance/authorization before recommending changes. Experiment evidence may live on the active experiment branch rather than `main`. Use current Core naming and routing; preserve historical AETHER-CL identifiers. This rule does not authorize a new experiment or override Core/02W gates.

### Separate research interest from execution impact

`READ`, `DEEP DIVE`, and `REPRODUCE` remain candidate dispositions, not commands to start work and not claims of completed reproduction. Give material findings a separate execution-impact assessment:

| Impact | Meaning |
| --- | --- |
| **MONITOR / BACKLOG** | Preserve the source and implications. No change to active work. Default. |
| **NEXT-CHECKPOINT CANDIDATE** | Could address a demonstrated bottleneck or provide an important comparator. Core considers it at the next bounded review. |
| **IMMEDIATE REVIEW** | Evidence indicates a safety issue, invalid measurement/comparison, broken dependency, or decisive feasibility problem in the current study. Explain the exact affected assumption. Core/engineering decides whether to stop or repair. |

A newer model, higher leaderboard score, or overlapping architecture name alone is not a reason to interrupt a valid experiment. Prior art can require revising a novelty claim without making the current instrument, baseline, or ablation useless.

### Protect a bounded experiment

Do not change its task, baseline, evaluation split/seeds, intervention, metrics, or resource budget mid-study because of a frontier item. Necessary corrections require a documented amendment and clear separation from frozen evidence. Review normal design changes at the agreed milestone boundary. A documented infrastructure blocker is not a reason to restart architecture design from scratch.

Default to one active core hypothesis-driven experiment per owner, with a small next-step shortlist rather than activating the whole reading queue. A parallel independent hardware/engineering branch may continue. Any added experiment must identify its owner, measurable question, baseline, minimal intervention, feasible resources, completion criterion, and what it replaces or why capacity exists. Core/HQ retains approval authority.

### Required execution-impact footer

End each weekly report with:

- **Continue:** current authorized work / documented next gate.
- **Change now:** none, or a specific urgent concern and affected assumption.
- **Next checkpoint:** normally at most one strongest new experiment candidate; zero is valid.
- **Deferred:** important findings that do not change the present workload.
- **Evidence produced:** distinguish sourced reading, implementation/tests, native runs, and audited results; report no verified new execution evidence when applicable.

**"No change to the active experiment; continue" is a useful Frontier Watch outcome.**

### Cross-project reuse

Embodied-AI's broad learning/model/simulator milestones are not AURA's engineering status. Share pinned environments, adapters, protocols, and evidence where compatible, but do not reset AURA to first-simulator selection or duplicate the same experiment across projects. One deliverable should have one owner; a separate run is justified when the research question or evaluation conditions differ.

Upstream summaries are research leads, not independent corroboration. Re-check load-bearing primary claims before promoting them into architecture evidence. Published author results, accessible code, locally executed tests, and independently audited runs are distinct evidence levels.

## Reading order

1. `CURRENT.md` — active AURA radar and current priorities.
2. `TREND_LEDGER.md` — persistent hypotheses and accumulated evidence.
3. `YYYY/YYYY-MM-DD.md` — dated reports and handoffs preserving the evidence trail.
