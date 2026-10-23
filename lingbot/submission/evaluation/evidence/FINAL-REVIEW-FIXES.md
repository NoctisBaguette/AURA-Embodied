# Final B CPU repair re-review — 2026-10-22

CPU deliverable SPEC verdict: **PASS**. CPU deliverable QUALITY verdict: **PASS**.

All three Important findings remaining in `FINAL-REVIEW.md` are **ADDRESSED**. No new Important defect caused by this repair wave was established. This closes the reviewed CPU blockers in combination with the preceding scoped aggregation and runner reviews; it does not grant native integration or final competition acceptance. Native/model loading, parity, simulator task execution, real interruption/resume and throughput remain **NOT RUN**. All records used below are synthetic, with zero real policy episodes.

## Reviewed versions

Frozen root snapshot `review-final-fixes-snapshot.txt` SHA256:
`7ea72859ea8b27ee602e365921e84188d125913ddf3262d6e7286296b6601387`.

Production SHA256 values:

- `evaluate.py`: `6426276104e62473373720983687c20c958d80203f2cd2789b63cb4f4e72b11c`
- `ledger.py`: `ed8d773f943377d07f2af8749b541ff2184edc3d63f0c55971fba9f20bb088c6`
- `aggregate_results.py` (unchanged): `fd0526dbccad64f88bd20ec71d59fa94a0785f576087adf38e7d77210808a57c`

Probe subprocess fixture `tests/fake_backend.py` SHA256:
`5d197c000ea2b4d980d8effdfb3da6c1655292480cc67a3e263f0d5f5ded4301`.

## Scoped findings

| Remaining Important finding | Verdict | Independent evidence |
|---|---|---|
| Full attempt stream retention | ADDRESSED | stdout/stderr are exclusive binary files, their paths survive in terminal execution evidence, and full beginning/end markers survive >6,000-character outputs for success, crash, invalid JSON and timeout. Typed rejection retains its JSON stream and empty stderr. Failure action count remains nullable. |
| Evidence kind versus run configuration | ADDRESSED | Configured evidence kind is checked by begin and STARTED reads. Synthetic real-policy relabeling against a fixture config is rejected on both paths, including a deliberately recomputed record hash. The same check rejects configured stage/hash mismatch. Existing STARTED/terminal/child checks extend this enforcement to terminal reads/writes. |
| Complete-episode video status mismatch | ADDRESSED | A backend's PENDING video status now yields an immutable INFRA_ERROR with the validation reason, instead of COMPLETE_POLICY. Valid NOT_REVIEWED fixture completion remains accepted. Source permits the same optional REVIEWED/NOT_REVIEWED status vocabulary as aggregation and retains the null-video requirement. |

Runner-measured wall time remains the fallback when the backend supplies no valid wall time; complete responses retain backend-reported wall_seconds. This review's PASS does not interpret that value as independently measured end-to-end native throughput.

## Reproduction and observed output

From workspace root:
`python lingbot/submission/evaluation/evidence/final-review-fixes-probes.py`

The script loads frozen production source in memory, copies the identified CPU fixture into a temporary directory and removes its synthetic records afterward. It is a bounded review probe, not a repeat of the routine suite.

```text
large_success COMPLETE_POLICY retained_stream_bytes 6765 6019
always_reject REJECTED_SETUP retained_stream_bytes 450 0
large_crash INFRA_ERROR retained_stream_bytes 6031 6031
large_invalid_json INFRA_ERROR retained_stream_bytes 6029 6029
sleep INFRA_ERROR retained_stream_bytes 6035 6035
pending_video INFRA_ERROR retained_stream_bytes 736 0
ledger evidence_kind write_and_read_rejected
ledger stage write_and_read_rejected
ledger checkpoint_manifest_sha256 write_and_read_rejected
```

The initial probe harness attempted to extract the test fixture from a snapshot that contains no such entry and failed before executing checks. The harness was corrected to copy the separately hashed fixture above; the displayed successful run follows that correction. No production defect was inferred from the harness error.

The implementer's `final-fix-wave.md` reports 50 passing tests. This reviewer did not rerun that suite or independently certify its output; the parent is checking the receipt. Existing native dependency limitations remain explicit and unchanged. Review complete; no further code probes or modifications planned.
