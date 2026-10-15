# Reproducible local GPU serving lifecycle

`scripts/apertus_lifecycle.py` is a Python standard-library tool intended to run **on the already authorized GPU host**. It neither connects by SSH nor downloads anything. Its Docker operations are covered by isolated subprocess-boundary tests. These tests are not evidence that the model fits GPU memory or performs extraction correctly.

The serving image and model are pinned:

- Image: `ghcr.io/swiss-ai/vllm_apertus_1.5_release@sha256:d85533f251c8272218ae2e519510836376e5a335b44f2204f193018e37753bc6`.
- Repository/revision: `swiss-ai/Apertus-v1.5-8B`, `ef4bbc54d6fe658bc782280ff9f3b53a10a9758f`.
- Trusted manifest: [`deploy/apertus-model-manifest.json`](../deploy/apertus-model-manifest.json), SHA256 `b467d83827cfad858f7edc524c47e4db74811d9e8f4cfedbc14c656e312b9a7b`.
- The manifest covers all 23 files, totaling 18,441,320,470 bytes. Large-file hashes come from upstream LFS metadata; small-file SHA256 values were computed after validating their exact pinned-revision downloads against upstream Git blob hashes.

The actual pinned image's CLI and text-only tower-loading implementation were inspected before choosing the arguments. The initial settings were candidates: 32,768 context tokens, one sequence, 2,048 batched tokens, 0.9 GPU utilization, eager execution, and no CPU offload. **Measured on the authorized RTX 5090 Laptop host (23.4 GiB):** other containers that are not stopped keep about 2.4 GiB, so only 21.0 GiB was free and 0.9 utilization failed at startup; 0.88 with a 2 GiB CPU offload loaded the weights but left 3.83 GiB of KV cache against the 4.0 GiB that 32,768 tokens need; **0.89 utilization with a 2 GiB CPU offload started and reported 4.07 GiB KV cache (33,312 tokens, 1.02× concurrency at 32,768)**. `--gpu-memory-utilization` (0.5–0.95, default 0.9) is a `prepare` option for this reason. `--max-context` accepts 4096–32768; `--cpu-offload` (also `--cpu-offload-gb`) accepts 0–16 GiB. Changing these requires a stopped lifecycle followed by `prepare` again.

This deployment uses `--language-model-only` and `--skip-mm-profiling`. The application supplies text extracted from complete source PDFs; it does not establish image or audio inference capability. Server readiness alone does not prove that the largest complete request fits the configured context or memory budget.

## Files to place on the host

Copy the script and trusted manifest together, or preserve their repository locations. Complete the official model download separately. The expected weights directory is `~/tenderproof/models/Apertus-v1.5-8B`. Keep the downloaded files unchanged while this lifecycle is active.

Choose a private environment-file path outside the model directory. `prepare` creates a new cryptographically random API key in a mode0600 file **only when that file is absent**. It never replaces or prints an existing key. An existing file must be current-user-owned, mode0600, and contain exactly one line:

```text
VLLM_API_KEY=<32–256 characters from letters, digits, dot, underscore, tilde or hyphen>
```

The operator must securely synchronize this key with the authorized client's ignored `LLM_API_KEY` configuration. The key itself must not appear in command arguments, printed output, tracked files, or copied logs. Do not use the application `.env`, which may contain other settings or HF credentials. The serving environment accepts no HF token. Keep the authentication file and lifecycle state outside the model directory.

The following commands use the profile observed to work on the authorized host. They assume the script and manifest are adjacent under `~/tenderproof`. If a stopped lifecycle already has this saved profile, use `start` directly; run `prepare` only to initialize or intentionally change its configuration:

```sh
python3 ~/tenderproof/apertus_lifecycle.py prepare \
  --manifest ~/tenderproof/apertus-model-manifest.json \
  --model-dir ~/tenderproof/models/Apertus-v1.5-8B \
  --auth-env ~/tenderproof/runtime/vllm-api.env \
  --stop-workload llama-qwen35 \
  --stop-workload visionx-triton-face-local \
  --max-context 32768 --cpu-offload 2 --gpu-memory-utilization 0.89

python3 ~/tenderproof/apertus_lifecycle.py start --startup-timeout 900
python3 ~/tenderproof/apertus_lifecycle.py status

# After authorized inference and evidence capture, or to recover an interrupted start:
python3 ~/tenderproof/apertus_lifecycle.py stop
```

For a client on another host, use the current `endpoint` returned by `status` as the private SSH forward destination. Its bridge IP can change after each start; do not reuse an old IP or the obsolete host port `18101`. Forward only to the endpoint of this owned container, keep the client listener on loopback, and verify authenticated model access through the application network. Do not depend on a tunnel script stored in an agent's temporary scratch directory.

Without explicit `--stop-workload` arguments, no existing workloads are stopped. Only the two authorized names above are accepted. The script never searches for GPU processes to kill. Already stopped workloads remain stopped. Existing unrelated containers remain untouched.

## State and restoration

`prepare` verifies the manifest's own pinned hash, then the size and SHA256 of every listed model file. It validates the settings and explicit stop list, creates the authentication file only if absent, and validates its permissions/content. It does not stop workloads or create a serving container.

`start` repeats the full file verification, confirms that the pinned image is already present, records all running container names, and records exact IDs and initial running states for the authorized workloads. It persists stop intent before each stop attempt and completion afterward. It creates a uniquely named, task-owned **internal Docker network**, stops only the specified workloads that were running, and launches the task-owned `tenderproof-apertus` container. No image pull is permitted.

The container is **not published on any host port**: Docker ignores `--publish` on an `--internal` network (observed on the real host: `docker port` was empty and `127.0.0.1:18101` refused connections). Readiness and clients use the container's private bridge address on its task network, which `start` discovers and records as `endpoint` (for example `http://172.19.0.2:8000/v1`); only a private IPv4 address is ever probed. The container runs as the invoking host user (`--user <uid>:<gid>` with `USER`/`LOGNAME` set, because the image has no passwd entry for that uid) so it can read the private weights and write its private cache with every capability dropped. It mounts `/models/apertus` read-only, uses a read-only root filesystem and private writable cache/tmp/shm, and sets offline/telemetry-disable flags. Request/output logging is explicitly disabled using the verified `--no-enable-log-requests` and `--no-enable-log-outputs` flags. The application's separately configured private inference traces remain the evidence record. The API key is supplied by private `--env-file`, never as a key value in argv. The script does not dump Docker diagnostics, container environment, HTTP headers, or response bodies. Status reports are credential-free.

Readiness requires an authenticated model-list response naming the expected repository and a 401 response to unauthenticated model-list access. Startup failure, timeout, or handled interruption triggers cleanup and restoration. `stop` removes the serving container, restores the exact originally running IDs with recorded stop attempts, and removes the task-owned network. It checks whether each ID is already running before starting it. It never substitutes a new container that happens to reuse an old name. Failed restoration remains `restore_pending`; repeat `stop` after resolving the reported Docker/container problem.

State and events are written atomically under `~/tenderproof/runtime/apertus-lifecycle` with a lock, mode0700 directories and mode0600 state files. Repeated successful `start` or `stop` calls do not repeat workload stops or restoration. An already-running lifecycle's `start` returns its current readiness, rather than silently replacing a failed container; use `stop` then `start` for an intentional new attempt.

Before removing its owned serving container on startup failure or `stop`, the script attempts to preserve recent stdout/stderr in `~/tenderproof/runtime/apertus-lifecycle/diagnostics/<UUID>.log`. It verifies ownership and the recorded container ID first, then requests only that exact container's last 1,000 log lines. Capture stops after 256 KiB or five seconds, with at most one additional second to reap the diagnostic Docker CLI process. It never collects another workload's logs or container environment. The diagnostics directory is mode0700 and files are mode0600; raw log contents never appear in status, state events, console output, or public reports.

The actual launch API key is redacted before writing, including a partial key at the capture cutoff. `start` records only its SHA256 fingerprint privately. If the authentication file is missing, changed, or cannot be matched to that launch fingerprint, capture is skipped rather than saving potentially unredacted logs. Keep the key file unchanged until `stop` finishes. Capture errors, unavailable storage, and log-command timeouts do not prevent container removal or workload restoration. Private events record only capture availability, filename, byte count and termination metadata. These bounded logs may be incomplete; keep them private and review them locally before deciding whether any excerpt can be shared.

SIGKILL, host power loss, or Docker failure can prevent immediate cleanup. Preserve the state directory and run `stop` to recover. Do not manually replace containers or change this state during an active lifecycle. If the serving name has been replaced by an unowned container, the script refuses to stop it or restore competing GPU workloads; the operator must resolve that ownership conflict explicitly. This is a bounded lifecycle tool, not a host supervisor.

A failed Docker inspection is not treated as absence. A successful complete container/network listing must confirm that the exact object is absent. If inspection fails and the object is still listed, or the listing also fails, cleanup remains pending and no competing workloads are restarted while the serving container's state is uncertain. This behavior addresses independent review finding GL-01.

## Validation checklist for each new host

The operator must check actual network isolation and serving diagnostics, run the complete authentic application request, verify its token/memory budget, preserve real request/response evidence, and then execute `stop` and confirm restoration. Successful software tests or an authenticated model list are not a benchmark, a successful full-source inference, or a model-quality claim.

Local software verification: `.venv/bin/python -m pytest track_2b/tests/test_gpu_lifecycle.py -q` — **44 passed in 0.33s** (the real host exposed three lifecycle defects that mocked tests could not: root with dropped capabilities could not read the 0600 weights or write the 0700 cache, `--publish` is ignored on an internal network, and 0.9 utilization exceeded free memory; each now has a regression test) after adding private diagnostic capture. Coverage includes ownership/ID and ambiguous-inspection boundaries, API-key redaction, file permissions, byte/time limits, startup-failure capture and restoration despite capture/storage/key failures. Docker and HTTP boundaries are mocked; these tests do not launch a model. Independent re-review previously accepted the GL-01 fix. This isolated software test command did not execute remote lifecycle commands. Completed genuine host execution is documented in REAL_MODEL_INTEGRATION.md and the final submission verification record.

Earlier full local suite after the reviewed lifecycle and nullable-configuration changes, before this diagnostic addition: **219 passed in 16.54s**.
