# AURA-Embodied Experiment Log

This document records reproductions, implementations, modifications, evaluations, and experimental findings.

Experiments should preserve not only results, but also reasoning and failure analysis.

---

# EXP-0001 Preparation

Date: 2026-10-04

AETHER-CL Prototype A asks whether explicit verification and bounded recovery
improve manipulation autonomy under disturbances with a fixed policy.

Milestone 0 prepares an isolated simulator environment, finite random-action
smoke tests, episode logging, and a browser viewer for the A100 server. This is
infrastructure preparation; it does not yet produce manipulation-policy or
verification/recovery results. Server physics and rendering validation are pending.

See [the milestone plan](docs/research/experiments/AETHER_CL_M0_Environment_Plan.md)
and [implementation instructions](aura-sim/prototype_aether_cl/README.md).

Deployment update (2026-10-05, project timezone): direct server retrieval was
replaced by laptop downloads and SSH transfer. User-provided output confirms the
repository arrived via Git bundle and `aether-cl` was copied offline from
`robotwin-sim`. The copied package inventory guides an incremental Linux/Python
3.10 wheel set; it does not establish successful simulator execution. Installation,
native imports, physics, and rendering remain server acceptance steps.

---

# Experiment Template

## Experiment ID

Example: EXP-0001

## Date

YYYY-MM-DD

## Research Question

What are we trying to understand?

## Hypothesis

What do we expect?

## Background

Existing system, paper, or baseline.

## Method

Implementation and experimental approach.

## Environment

Hardware:

Software:

Dataset:

Simulation:

## Baseline

What are we comparing against?

## Metrics

How is success measured?

## Results

## Failure Analysis

What failed?
Why did it fail?

## Lessons Learned

## Next Direction
