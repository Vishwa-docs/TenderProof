# Apertus access and provisioning

Checked 15 October 2026 against the organizer's [Resources & Tools](https://hackapertus.notion.site/resources-tools).

- CSCS inference API: the organizer says all available keys were distributed and new requests closed 6 October, 18:40 CEST.
- Phoeniqs compute: new applications closed 4 October, 20:30 CEST.
- Academic access depends on institutional eligibility; none is assumed for SwissChivers.
- The user has requested the advertised $10 Hugging Face credit and obtained access to the official Apertus 1.5 8B model. The account still showed USD 0.00 credit on the latest 15 October check. No paid cloud endpoint has been created.

## Current local deployment work

The user authorized their GPU machine and temporary suspension of two specified existing inference containers, with restoration after testing. The machine has an NVIDIA RTX 5090 Laptop GPU with 24 GB VRAM. Initial other workloads occupy approximately 21 GB. Downloads run without stopping those workloads.

The official model revision selected for download is `ef4bbc54d6fe658bc782280ff9f3b53a10a9758f` of `swiss-ai/Apertus-v1.5-8B`. The supported serving image has been verified locally at `ghcr.io/swiss-ai/vllm_apertus_1.5_release@sha256:d85533f251c8272218ae2e519510836376e5a335b44f2204f193018e37753bc6`. The [official model card](https://huggingface.co/swiss-ai/Apertus-v1.5-8B) requires its custom vLLM/Transformers implementation. Generic vLLM or Ollama compatibility is not assumed.

At this checkpoint, the model download remains in progress and the serving image is available. No successful Apertus inference or model-quality result is claimed here. The local application virtual environment is installed. The GPU-host virtual environment exists, but its optional Python package installation hit a network timeout; the Docker serving path does not depend on that installation.

The [GPU lifecycle guide](../../docs/GPU_SERVING_LIFECYCLE.md) documents pinned file verification, private authentication, explicit authorized workload suspension, loopback/offline serving, and restoration by recorded container ID. Its script and isolated software tests are prepared; they do not establish memory fit or actual inference success. Initial text-only settings use zero CPU offload, with a 2 GiB fallback available for actual startup diagnosis.


## Configure an Apertus endpoint

Run `make setup-access` to create private local configuration, then set `LLM_BASE_URL` (including `/v1`), `LLM_NAME=swiss-ai/Apertus-v1.5-8B`, and `LLM_API_KEY`. Keep credentials in ignored `.env`/`.runtime` files. The official model's thinking mode is disabled for structured extraction.

The app and worker use an internal Docker network. `model-relay` accepts only model-list and chat-completion routes and forwards to a fixed Docker Desktop host address, port 18102. That port is intended for an SSH tunnel to the GPU's loopback-bound model server. Set `LLM_BASE_URL=http://model-relay:8081/v1` for this topology. The relay publishes no host port and is not a general egress proxy. An arbitrary external URL in `.env` does not make it reachable from the internal network.

Keep the model API bound to loopback, authenticated, and accessed through the authorized SSH connection. An API key alone does not protect every vLLM route; see [vLLM security guidance](https://docs.vllm.ai/en/stable/usage/security/). This is customer-controlled local infrastructure; it does not establish that the GPU is physically in Switzerland or meets a hosting certification.

## Evidence required for readiness

Run actual inference on the complete authentic GPA source PDFs, preserve page/source references, record model/image revision and latency, inspect proposals before approval, and verify missing evidence stays unknown. Software tests with controlled HTTP responses are not model evaluations. No synthetic source package or fabricated test report is permitted in the application or submission. After testing, stop the temporary Apertus workload and restore the authorized existing services.
