# AURA Research Workbench and Open Technical Portfolio — proposal

Date: 2026-11-12. Status: **PROPOSED FOR USER / HQ / CORE REVIEW**, not an approved architecture, platform purchase, teammate assignment or experiment authorization.

[简体中文配套](AURA_Research_Workbench_Proposal_2026-11-12.zh-CN.md)

## 1. Recommendation

Keep the **research objective stable and technical implementations contestable**. AURA should investigate affordable, reliable manipulation transfer rather than identify itself with one policy, world model, memory design or verification wrapper. Protecting the scientific scope of an active experiment does not mean constraining the whole team's exploration to that experiment.

Create a shared **research-to-development workbench**, not another chronological paper archive. It should connect external evidence, candidate mechanisms, AURA's actual capabilities, alternative system configurations, experiments and decisions. The central question for a teammate should be: **What can this help us do, what is supported, what remains uncertain, and what small piece of work would resolve the uncertainty?**

Recommended implementation order: pilot an existing collaborative relational workspace, retain GitHub for code and accepted evidence, and add a thin custom comparison interface only if the pilot exposes a specific unmet need. Feishu Base is the first off-the-shelf candidate for a Chinese-first team workspace; Notion is an alternative when existing team usage/access or its available ChatGPT integration makes it more practical. Actual access, permissions, export and integration must be tested before selection. No platform has been selected or deployed by this note.

## 2. Project context and boundaries

The inspected current architecture already states that models are replaceable capabilities, representations may be explicit/learned/latent/hybrid, and transfer across objects, tasks, environments, embodiments and experience is central [P1]. The roadmap retains both physical picking/soft-grasping work and controlled simulation research [P2].

Core continuity v0.2 describes the narrow M9a commissioning route and separate Core acceptance before fresh evaluation [P3]. This proposal changes none of that. It does not verify present server health or override the operator's pause. Historical AETHER-CL identifiers remain; public identity is AURA and BAGUETTE is provisional internal Core naming.

The latest inspected frontier radar is the November 5 update [P4]. Its source list is background, not a newly revalidated literature review in this proposal.

## 3. Where AURA can create value

A useful candidate thesis is: **make manipulation capabilities easier to transfer, combine and deploy under limited target-domain data, engineering effort and compute**.

A contribution need not be a newly pretrained foundation model. A small mechanism, dependable integration, controlled benchmark protocol or explanation of a failure can be valuable if the claim is precise and supported. Conversely, assembling existing APIs or making a model smaller does not alone prove scientific novelty or reliable transfer.

For every transfer proposal record:

| Element | Required description |
| --- | --- |
| Source and target | Which objects, environments, sensors, robot/action interfaces, data distributions or compute devices differ? |
| What stays fixed | Policy weights, task, verifier, controller, budget and/or training data as applicable |
| Allowed adaptation | Zero-shot, calibration, demonstrations, adapter training, fine-tuning or code changes |
| Cost | Target data, GPU time, integration/calibration effort, memory, latency and intervention cost |
| Evidence | Held-out target conditions, clean/source results, uncertainty, failures and regressions |

Data-format conversion, dataset-domain transfer, embodiment transfer and policy-backend portability are different claims. A common interface is not evidence that a policy works on a new robot. Compression/deployment work should measure a reliability/resource trade-off on source and target conditions, not only checkpoint size or average inference time.

## 4. Modularize interfaces, not assumptions

Distinguish three meanings of modularity:

- Functional: perception, state/history, action, verification and recovery can be discussed separately.
- Software: components can be accessed through declared interfaces.
- Learned representation: trained internal components can be independently exchanged without losing performance.

The first two do not establish the third. Preserve an integrated model as one module when its internals are jointly trained. Support explicit state, latent context and a no-extra-memory baseline as alternatives. A universal symbolic ontology or an online world model is not a prerequisite.

A policy adapter contract must include observation modalities, preprocessing/normalization, state/history requirements, action representation and units, coordinate frames, relative/absolute conventions, action-chunk duration, control frequency, reset/session semantics, model version, and missing/stale-input behavior. A separate robot adapter handles supported actuation and runtime constraints. Unsupported combinations should be rejected, not silently translated.

Reuse existing foundations where compatible. LeRobot documents composable observation/action processors [S1]; openpi documents remote policy serving with a lightweight robot-side client [S2]. These are implementation references, not mandates to replace AURA's current environment or claims of universal compatibility.

### Illustrative route recipes, not approved experiments

| Recipe | Composition | What it would test |
| --- | --- | --- |
| R-A: explicit supervisory route | Compatible controller/policy + geometric/task state + temporal outcome checks + bounded recovery | Can a small explicit mechanism improve reliability under shift? |
| R-B: integrated learned route | Pretrained temporal/latent-state policy + necessary runtime constraints; no mandatory external memory/world model | Does a simpler integrated model achieve the required reliability/cost? |
| R-C: efficient adaptation route | Compatible pretrained policy + calibrated sensor/action adapter + one compression or lightweight adaptation mechanism | Can target capability be retained at lower compute or adaptation cost? |

Do not train all recipes simultaneously or enumerate every possible combination. Use a few meaningful alternatives and staged ablations. The workspace must show incompatible and untested combinations, not just attractive diagrams.

## 5. Information model: reusable records rather than weekly copies

Maintain stable IDs and typed links. A weekly issue is a view over records, not their only home.

| Record family | Minimum useful content |
| --- | --- |
| Sources and claims | Paper/model/dataset/repository identity and version, dated primary link, mechanism summary, evidence and limitations, artifact readiness, first/last check, both-watch provenance, human corrections |
| Capabilities and modules | Purpose, inputs/outputs, assumptions, requirements, implementation/reference link, compatibility, evidence status |
| Candidate systems | Exact chosen module versions, compatible interfaces, target scenario, estimated resource envelope, alternatives and open risks |
| Experiments and results | Question, baseline/treatment, source/target split, fixed variables, adaptation budget, protocol/commit, actual receipts, results and failure cases |
| Decisions and work | Options, rationale, approval/status, owner/reviewer, bounded deliverable, dependencies, acceptance criteria and next review trigger |

A method may have multiple claims with different evidence levels. Distinguish an author's measurement, an accessible artifact, inspected code, local tests, native execution and an accepted audited result. Unknown is not failure; not reported is not unsupported; not investigated is not absent.

Keep two assessments on each source: **what the work claims in its own right**, and **AURA's current relevance interpretation**. The second may change as our questions evolve. Store evidence beyond the current narrow filter without turning every item into a deep dive or assignment.

## 6. User-facing views

### A. Research library / discovery inbox

Searchable visual cards with short Chinese summaries and English toggle, source identity, mechanism, capability tags, artifact state, limitations, last check, reviewer and links. Teammates can submit a URL, short note, image or video reference without filling a long form. AI-assisted extraction creates a draft, not a verified claim.

### B. Capability comparison

Select a capability such as task-state maintenance or camera-domain adaptation; compare relevant external methods and **the exact version of our own implementation** side by side. Rows include input privilege, action interface, training requirements, memory, latency, demonstrated transfer, recovery and availability. Each cell opens its evidence and setting. Different benchmark numbers are not directly ranked. Do not reduce the comparison to unsupported green ticks or star scores.

### C. Candidate system recipes

A readable configuration table shows module choices, dependencies, incompatible interfaces, compute assumptions and which components are optional. Later, a small custom side-by-side interface may improve this view. No drag-and-drop architecture editor or execution orchestrator is required in version one.

### D. Experiments and decision queue

Show proposed questions, approved protocols, blocked runs, returned evidence and decisions separately. A paper marked READ or REPRODUCE is not an approved task. Every proposed experiment should say what decision its result would change and what would count against the hypothesis.

### E. My work / meeting view

A teammate sees the assigned question, prerequisite reading, exact artifact to return, reviewer and done criteria. A meeting view shows what changed, two or three relevant alternatives, the open decision, disagreement and the next evidence request. Casual short meetings can work from this view without mandatory presentation decks.

## 7. Example interaction

Illustrative question, not an approved study: **Can a cheaper camera configuration retain reliable placement in a changed workspace?**

The team opens the transfer question, selects two or three sensing/policy configurations and sees primary evidence beside our own capability status. One person checks calibration/interface compatibility; another evaluates a small model-adaptation option; another prepares target-scene labels and failure metrics. These are complementary bounded deliverables, not permanent departments.

The resulting decision might be to retain the original system, run a small adapter study, or reject an expensive route. The decision links to the evidence and experiment it affects. A result that rejects a route is still useful. The next Frontier Watch update can then flag a genuinely relevant new method without reopening unrelated choices.

## 8. Reliable updates and sharing with AI chats

Proposed update pipeline: both watches and teammate submissions -> canonical source IDs/version matching -> AI draft fields -> human review where consequential -> linked records/views -> revisioned decision snapshot.

Deduplicate by paper/model/repository identity and revision, not title alone. Preserve both projects' relevance judgments on a shared source instead of manufacturing independent corroboration. Revisions update the existing record with a visible change log; they must not overwrite human notes, accepted decisions or execution status.

Use explicit field ownership:

| Authority | Owns |
| --- | --- |
| Collaborative workspace | Intake, draft source cards, working comparisons, discussion and unapproved research questions |
| GitHub engineering issues/PRs, when activated | Implementation ownership/status and code review; workspace mirrors links rather than a competing status |
| Versioned repository evidence | Approved protocols, code, experiment receipts and accepted decisions maintained by their existing owners |

Start with controlled imports and versioned exports rather than ambitious bidirectional synchronization. Later API integration needs authentication, scopes, conflict detection, stable record IDs, retries and audit logs. A record update must not change its evidence level automatically.

An **export discussion packet** should preserve selected record IDs, source versions/links, Chinese/English summaries, chosen comparisons, current AURA revision/scope, alternatives, unresolved questions, decisions and evidence manifest in Markdown plus structured JSON. This provides useful context to HQ/02 or another AI even without access to the live platform. CSV alone may lose relationship semantics; export explicit foreign IDs and test restoration [S6]. Large raw videos/logs remain in appropriately controlled storage with hashes and locations, not copied into every packet.

Failed watch/import jobs must show last successful update and missing coverage. A visible failure or stale marker is preferable to an apparently fresh but incomplete workspace. This proposal does not create an autonomous refresh service.

## 9. Platform choice

| Option | Verified useful capabilities | Main trade-off / assessment |
| --- | --- | --- |
| Feishu Base + documents | Gallery/table/board views, linked records, forms and collaboration/permission features; record APIs [S3,S4] | First pilot candidate for Chinese-first team interaction. Account access, quotas, permissions and authenticated export need testing; not connected here |
| Notion databases | Gallery, relations, comments and Markdown/CSV exports [S5,S6] | Reasonable if team access/usage is easier. A Notion integration was discoverable but is not connected. Relation exports need explicit preservation |
| GitHub Issues/Projects | Code-linked issues, tables/boards/roadmaps, custom metadata and automation [S7] | Best fit for engineering execution evidence; less suited as the sole visual research-comparison surface |
| Fully custom application | Can implement exactly the proposed comparison/recipe interactions | We would own authentication, access control, collaboration, editing, storage and maintenance. Do not begin here |

**Proposed choice:** an existing collaboration tool for the pilot; GitHub remains the evidence/code backbone. Choose one collaboration tool, not Feishu plus Notion plus another task tracker. Custom development should be limited initially to import/export validation and, if needed, a thin comparison viewer.

Do not confuse a static visual prototype with a shared application: local browser edits are not team persistence. GitHub Pages is static hosting, and public publication can expose material even when a source repository is private [S8]. Use a public literature layer and a properly permissioned team layer for private notes, unreleased results, budgets and access details. Never embed credentials in a client page. Public-repo availability is not consent to publish all future team material.

## 10. Pilot scope and acceptance

Proposed pilot: roughly 15–25 representative source records from existing watches, three candidate recipes, two or three real project bottlenecks, one actual existing experiment record, and a small set of selectable work packages. These are design targets, not items already imported. Include methods that challenge our current route and at least one unavailable/incompatible artifact.

The pilot passes only if teammates can:

1. Submit a source without editing Markdown or duplicating an existing record.
2. Find relevant methods and explain how two alternatives differ using evidence.
3. Distinguish published claims from AURA's own measured results.
4. Locate their actual task and understand its completion criteria.
5. Record a decision, dissent and a later review trigger without silently rewriting history.
6. Ingest a repeated/changed watch without losing annotations or inventing new tasks.
7. Export and reopen an AI-readable packet with relationships, versions and bilingual meaning preserved.
8. Demonstrate the intended access restrictions from an unauthorized or logged-out account.

Stop expanding the platform if maintaining it competes with the manipulation work. If existing views suffice after real meetings, do not build a custom application. If a named comparison is repeatedly painful, implement only that missing interaction.

## 11. Governance and next decision

HQ owns platform adoption, team access, scope and resource allocation. Core/02 owns the scientific comparison and accepted research direction. 05 produces evidence-linked candidate records and updates; 06 owns engineering evidence and runtime integration. A separate bounded workspace-design/implementation chat can own the pilot without absorbing Core or Frontier Watch.

Suggested team roles are source curation, sensing/interfaces, model/deployment feasibility and evaluation. They follow existing strengths but are not rigid assignments. Owners should own a question or deliverable, not be permanently confined to a module. All assignments remain unmade.

**Decision requested:** accept or revise this workspace concept, choose the collaboration pilot platform after an access/export check, nominate an owner and a firm pilot scope. Do not authorize new robot experiments simply by approving the workspace.

## Sources and provenance

Project files inspected on 2026-11-12:

- P1: `ARCHITECTURE.md`, blob `231db96942806576a6bc38fcc59415e2c1c92aae`.
- P2: `ROADMAP.md`, blob `f5db9be91dc876df325a9577b2adae5e446b107a`.
- P3: `docs/research/coordination/BAGUETTE_Core_Research_Continuity_v0.2.md`, blob `e0173154914e28a0e5d973965b297895e907bbe5`.
- P4: `docs/research/frontier_watch/CURRENT.md`, blob `df23e0541502525e064f7162abcf7a5ba68ab4e1`.

Official product/technical documentation checked on 2026-11-12; capabilities described, not installations or pricing audits:

- S1: https://huggingface.co/docs/lerobot/v0.6.0/en/introduction_processors
- S2: https://github.com/Physical-Intelligence/openpi/blob/main/docs/remote_inference.md — inspected blob `cf39bd5fb5d391cd12c2939bd32ce1e9d8b83dc9`.
- S3: https://www.feishu.cn/hc/zh-CN/articles/697278684206 and https://www.feishu.cn/hc/zh-CN/articles/653027931590 — official indexed descriptions; some full pages were not text-readable.
- S4: https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/create and https://www.feishu.cn/hc/zh-CN/articles/360049067527
- S5: https://www.notion.com/help/galleries and https://www.notion.com/help/comments-mentions-and-reminders
- S6: https://www.notion.com/help/relations-and-rollups and https://www.notion.com/help/export-your-content
- S7: https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects
- S8: https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site

**Evidence produced for this proposal:** project-context review, official documentation checks and a bilingual design proposal only. No live workspace, import pipeline, synchronization, deployment, model execution or teammate assignment has been created.
