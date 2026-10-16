# Judge quickstart

TenderProof uses authentic public procurement documents and genuine Apertus inference. It starts with an empty project. The submitted video shows recorded application states from the documented real run; it does not seed those records into a new installation.

## Prerequisites and startup

Use Docker Compose, Python 3.11+ and enough disk/RAM for the Docling image. The first build downloads parser dependencies and OCR assets. For extraction, provision the pinned Apertus v1.5 8B model under your administration; see `GPU_SERVING_LIFECYCLE.md` and `../deploy/apertus-model-manifest.json`. The documented working GPU profile uses 24 GB VRAM plus 2 GiB CPU offload. Model access is governed by the Swiss AI model terms. No paid cloud service is required.

```sh
cp .env.example .env
make setup-access
# Privately configure a reachable real Apertus endpoint and API key in .env.
make run
```

The UI is at http://localhost:8001. Connect using the token saved in `.runtime/operator_token`. The initial token is an engineer for the `default` project. Keep credentials private. Additional commercial/inspection principals must be configured by the operator; the UI cannot impersonate them.

The application and worker are on the internal `sovereign` network. The supplied model relay reaches a separate host tunnel on port 18102. `LLM_BASE_URL=http://model-relay:8081/v1` is appropriate only when that tunnel is actually running. For a different on-premise topology, configure a reachable authenticated service and an explicit relay/network route. `make run` starts the application stack, not a remote GPU or its SSH tunnel. An unavailable model returns an error; there is no substitute response.

## Complete authentic review path

```sh
make setup
make ingest
```

This fetches and hashes five complete originals and ingests them into the application. Source URLs are in `track_2b/data/sources.json`; originals remain in private ignored runtime storage. The full IFB includes the separate specification scans, so these attachments overlap. Scope is OP34276 item 2, three 750 kVA transformers; item 1 is excluded.

1. Open **Evidence**. Search `37,105.50` or `24 weeks drawing approval` in the uploaded purchase order.
2. Open a result and inspect its original page. Check the source hash, page number, context, and duplicate citations.
3. Run actual Apertus extraction from the source inspector when the model endpoint is available.
4. Open **Overview** and **Review issues**. Follow each issue to its relevant source or pending record.
5. Review interpretations under **Requirements**. Input coverage does not establish semantic completeness.
6. Inspect **Supplier comparison**. Check unit-price bases and delivery triggers before approving any offer.
7. Correct a wrong price through the source-linked correction action. The application preserves the original output and requires separate approval.
8. Open **Change history**. Compare stored revisions to inspect the changed fields and their source references.
9. Export a draft Markdown or JSON dossier from **Overview**. The export preserves pending states and grants no release approval.
10. Inspect **Acceptance & release**. The public case lacks applicable FAT results, actual unit identity, and approved unit drawings.

The recorded 57-page tender took 427.118 seconds across six complete input windows. Runtime varies with hardware and model settings.
Rejected rows, capped outputs, failed audits, and missing call accounting remain visible in the review queue.
Search ranks lexical relevance. Citation coverage counts linked spans. Neither value measures engineering correctness.

Source search works after ingestion without a model endpoint.
Requirements, offers, and extraction records require actual inference or authorized source-based entry.
Fresh installations do not contain the recorded private database.

The current build deliberately has no generic completion override for extraction assurance. A future scoped assurance-resolution workflow is required to resolve incomplete runs; approving retained rows alone does not clear missing obligations. Complete isolated QA cases exercise successful approval/export behavior; those cases are not runtime/demo data.

## Verification and stop

```sh
make check
make stop
```

`make check` runs software regressions and the frontend build. Recorded final result: 380 Python tests, 51 frontend tests, TypeScript and Vite passed. These counts are not an Apertus accuracy benchmark. `make stop` preserves named volumes. Restore any borrowed GPU workloads using the documented lifecycle `stop` operation after serving.

See `../track_2b/SwissChivers_Report.pdf`, `REAL_MODEL_INTEGRATION.md`, and `../track_2b/submission/VERIFICATION.md` for actual execution, provenance and limitations. The demonstration and code do not certify physical conformity or place an external purchase order.
