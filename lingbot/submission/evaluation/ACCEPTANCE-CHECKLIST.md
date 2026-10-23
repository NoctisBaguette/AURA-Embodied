# B review gates

| Gate | Required evidence | Native dependency |
|---|---|---|
| Official grid | same 50 task keys in both official template settings; exactly 100 cells; default 10000 target completions | no |
| CPU isolation | dry-run imports/starts no torch/sapien/model/physics | no |
| Identity | manifest file-byte SHA; stage; task; setting; seed; shard; episode; per-chunk request identity; output locations | no |
| Resume | old records retained; identical duplicates dedup; conflicting physical episode identity rejected; config/hash changes rejected; unresolved starts block | no |
| Finite search | 1000 candidate proposal for target100; only audited typed setup rejections advance; fatal error stops shard | no for fixtures |
| Counts | bool false is counted failure, numpy.bool_ accepted; invalid types/counts/unknown cells rejected; partial envelopes preserve completed children | no |
| Exclusions | commissioning negative example and explicit fixture episodes produce zero real score | no |
| Error visibility | crashes/rejections/partial coverage/remaining work separate from official counts; no placeholder successes | no |
| Native contract | full upstream task action limit; exact settings/instructions; A loader and preprocessing; one policy | yes |
| Safe real rollout | one fresh-process native cell; interrupted/resumed evidence; real throughput including startup/setup | yes |
| Model decision | baseline and candidate identities separated; same task/setting/seed comparison; videos actually reviewed | yes |

CPU gates establish software behavior on labeled fixtures only. Native gates remain NOT RUN while required assets/runtime/evidence are absent. The full 10000 real episode target remains outstanding.
