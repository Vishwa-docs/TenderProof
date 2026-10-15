# Real Apertus integration — what the first live runs exposed

Recorded 15 October 2026. These are observations from running the pinned `swiss-ai/Apertus-v1.5-8B` (revision `ef4bbc54d6fe658bc782280ff9f3b53a10a9758f`) on the authorized RTX 5090 Laptop GPU through the deployed application. They are integration findings and defect fixes. **They are not a benchmark, an accuracy figure or an engineering review.** The package is a single incomplete public tender file set, and every proposal below is pending human review.

## Lifecycle defects found on the real host (mocked tests could not find them)

| Symptom | Cause | Fix |
| --- | --- | --- |
| Container exited in seconds with `PermissionError` on its cache | Root with `--cap-drop ALL` cannot read the mode-0600 weights or write the mode-0700 cache owned by the host user | Run as `--user <uid>:<gid>` with `USER`/`LOGNAME` set (the image has no passwd entry for that uid) |
| `Free memory ... (21.0/23.4 GiB) is less than desired GPU memory utilization (0.9)` | About 2.4 GiB stays in use by containers that are not stopped | `--gpu-memory-utilization` is now a validated `prepare` option |
| With 0.88 and a 2 GiB offload: 3.83 GiB KV cache against the 4.0 GiB that 32,768 tokens need | Context was kept at 32,768, as required | 0.89 with a 2 GiB offload: 4.07 GiB KV cache, 33,312 tokens, 1.02× concurrency at the full context |
| Server up but readiness never succeeded | Docker ignores `--publish` on an `--internal` network (`docker port` empty, loopback refused) | Probe and tunnel target the container's private bridge address; no host port exists |

Each failed start was cleaned up by the lifecycle and both authorized workloads were restored every time.

## Extraction defects found with real model output

| Symptom | Cause | Fix |
| --- | --- | --- |
| Supplier extraction from a bid abstract always failed validation | A bid abstract has prices but no guarantees, yet `facts` required at least one | `facts` may be empty; offers carry their own `source_ids`; a price or delivery value without an offer-level citation is rejected |
| Model labelled "24 weeks after approval of drawings" as 24 delivery weeks | No field for what the weeks are counted from | `delivery_basis`; only `project_start` is compared with a project-week milestone |
| Model put a three-unit lot total under a unit price | No price basis | `price_basis`; mixed or partly unstated bases are never compared like-for-like |
| Audit roles returned span-id lists, objects or truncated JSON | One vague shared prompt, `json_object` mode | Role-specific audit prompts and server-enforced `json_schema` decoding for every role |
| Requirements mapper counted `source_ids` upward until `finish_reason: length` | `json_object` mode does not enforce `maxItems` | Bounded decoding schema: at most 8 citations, 15 requirement rows or 20 offers, numeric values; Pydantic limits unchanged |
| One junk row discarded a whole run | All-or-nothing row validation | Invalid rows are rejected and disclosed verbatim in the trace and the event; **an identifier outside the window still fails the whole run** |
| Truncation was reported as a generic failure | No finish reason in the trace | `finish_reason` is recorded; truncation is named in the error |

## Known model limits seen in the saved proposals

- The 8B model often reads the wrong line-item column from flattened OCR tables, and it can shift amounts between bidders. The audit roles flagged some of these; they did not catch all of them.
- It can attach a lot total to a unit price basis, or label a fact with a property name that does not exist. Review each proposal against the original page.
- Requirement rows can cover the excluded 300 kVA item. A reviewer must reject them.
- A window that returns the row cap says so in its trace; more obligations may exist there.
- The four roles are one model with different prompts. Their agreement is not independent verification.

## What the proposals are

Every extracted row is `pending`. Nothing was approved, released or turned into a decision. Accepted rows are exactly what the model produced; rejected rows are kept verbatim in the trace.
