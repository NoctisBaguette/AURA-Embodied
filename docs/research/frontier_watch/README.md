# AURA-Embodied Frontier Watch

**Languages:** English · [简体中文 / Chinese reading index](README.zh-CN.md)

**Chinese companions published 2026-10-19:** [current radar](CURRENT.zh-CN.md), [October 19 decision brief](2026/2026-10-19.zh-CN.md), [evidence](2026/2026-10-19-evidence.zh-CN.md), [team work packages](2026/2026-10-19-team-work.zh-CN.md), [October 15 weekly report and linked appendices](2026/2026-10-15.zh-CN.md), and [trend ledger](TREND_LEDGER.zh-CN.md). The Chinese index pairs each file with its English source; earlier October 8/9 reports remain English-only.

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

## Decision-ready publication contract — 2026-10-19

User clarification: monitoring rules alone are insufficient. Each material update must leave enough **substantive technical and decision context** in GitHub for the user, HQ, Core/02 and teammates to act without a copied chat transcript.

### How much belongs in GitHub?

Use layered depth, not a fixed word quota:

1. **CURRENT.md:** the active decision summary, latest engineering context, changed priorities, unresolved choices, recommendation and links to supporting detail. Keep it navigable rather than accumulating every old table forever; preserve prior dated issues and Git history.
2. **Dated issue:** explain what each important method changes, why it matters for AURA, its capability, evidence/limitations and a feasible comparison. Include a cross-project delta; do not merely duplicate the upstream list.
3. **Evidence detail when needed:** exact primary links and IDs, source/version check dates, reported metric and conditions, artifact status, compatibility/resource constraints and what has not been verified. Distinguish similar names and citations. Keep unverified leads visible but separate from established claims.
4. **Decision/team detail when actionable:** options, recommendation, prerequisites, bounded deliverables, acceptance criteria, review owner, estimated effort, exclusions and the next approval gate. Assignees and decisions stay proposed until the user/HQ/Core actually assigns or approves them.

A significant item is not ready for decision handoff with only its title, score and a DEEP DIVE tag. The receiving reader should be able to answer: **What changes? What supports it? What are the alternatives? What would we build or test? What would it cost? What would completion look like? Who must decide?**

Do not paste full papers or all discussion. Preserve the reasoning and evidence needed for a decision, link deeper primary material, and attach technical detail where compression would hide an important limitation.

### Collaboration requirements

A proposed work package must include:

- one concrete question and the decision it serves;
- inputs with repository/branch/path or primary source;
- deliverable and proposed destination;
- testable acceptance criteria;
- dependencies, resource needs and explicitly labeled effort estimates;
- proposed role, reviewer, status and exclusions;
- distinction between preparation, implementation, native execution and acceptance.

A team may run independent approved packages in parallel. Protecting one experiment does not mean the entire team must wait or only one person can build. HQ chooses capacity and sequencing; Core resolves scientific scope; 06 controls integration and native evidence. Never mark people assigned, tasks accepted or other chats informed solely because a document was written.

### Update the decision record, not just the watch

Use local frontier packet IDs for proposed decisions rather than inventing global DEC IDs. Once reviewed, record approve/defer/reject, date, approver, reasoning, actual owner and evidence links. Keep prior alternatives and failed attempts traceable. Architecture decisions remain in the Core-owned records after review.

An explicit no-change decision is valid, but must be supported by a current-scope comparison. Execution protection must not become an excuse to omit new findings, implementation options or useful teammate work.

**Example complete handoff:** [October 19 decision brief](2026/2026-10-19.md), [evidence](2026/2026-10-19-evidence.md), [team work packages](2026/2026-10-19-team-work.md).

## Language and Chinese teammate companions — 2026-10-19

**User preference:** discussion with the user and the main research documents remain in English. Teammates need Chinese reading material. Future teammate-facing handoffs must therefore include a **Simplified Chinese companion**, not replace the English version.

The Chinese material must let teammates understand the work without reconstructing the English chat. Include the relevant research background, what changed across the watches, technical mechanism and AURA relevance, source/evidence limitations, alternatives and decisions needed, and the complete work-package instructions. Translate substantive explanations from the decision brief/evidence register where needed for the assigned work; a Chinese task title followed only by English links is insufficient. Full translations of external papers are not required.

For each work package preserve the same question, inputs, deliverables, acceptance criteria, dependencies, resource/effort estimates, reviewer, scope exclusions and approval status in both languages. Keep paper/model names, repository paths, commands, source links and IDs unchanged. Give important technical terms in Chinese with the English term on first use. Do not turn a proposed task into an approved assignment, remove uncertainty, or change numerical thresholds in translation.

Prefer separate linked files rather than doubling every paragraph inline. For example, a future `YYYY-MM-DD-team-work.md` can have a `YYYY-MM-DD-team-work.zh-CN.md` companion; provide a Chinese decision/reading brief too when its context is necessary for teammate decisions. These are naming examples, not claims that those files already exist.

Link the English and Chinese versions from each other and from the current handoff entry point. Identify the corresponding date/revision. Update both when scope, evidence, acceptance criteria or decisions materially change; explicitly flag a stale translation rather than presenting mismatched versions as synchronized. Check content parity before marking the bilingual handoff ready.

This requirement applies to future teammate handoffs. It does not itself claim that the historical English-only packets have already been translated, change the user's preferred discussion language, or authorize any new experiment.

## Reading order

1. `CURRENT.md` — active AURA radar and current priorities.
2. Latest dated decision brief and its evidence/team attachments, when present; use the linked Chinese companions for teammate-facing reading.
3. `TREND_LEDGER.md` — persistent hypotheses and accumulated evidence.
4. Earlier dated reports only when needed for provenance or a deeper comparison.
