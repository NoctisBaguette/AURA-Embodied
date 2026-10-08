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

## Reading order

1. `CURRENT.md` — active AURA radar and current priorities.
2. `TREND_LEDGER.md` — persistent hypotheses and accumulated evidence.
3. `YYYY/YYYY-MM-DD.md` — dated reports and handoffs preserving the evidence trail.
