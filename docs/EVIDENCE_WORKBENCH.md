# Evidence workbench

The workbench adds read-only investigation to the existing review and release controls.
Every result belongs to the requested project and its recorded snapshot.
No search, comparison or dossier export approves a claim.

## API contracts

All routes require the existing bearer identity.
The API checks project access before reading documents or snapshots.

| Route suffix | Result | Bound |
| --- | --- | --- |
| `/analysis` | Review issues, source coverage, lineage and release state | Bounded graph with truncation notice |
| `/search` | Ranked original passages with page and span citations | Query: 300 characters; results: 50 |
| `/snapshots` | Stored revisions and record counts | Latest 100 snapshots |
| `/diff` | Added, removed and changed records between stored revisions | Exact project-scoped snapshot hashes |
| `/dossier` | Reproducible draft review packet | Current package snapshot |

Prefix each route with `/api/projects/{project_id}`.
Search accepts `q`, optional `document_id`, and `limit`.
Diff accepts `from_hash` and `to_hash`.

## Retrieval and provenance

BM25 ranks lexical matches in the original parsed spans.
Numeric normalization matches equivalent decimal forms, including monetary amounts with trailing zeros.
The response keeps source text unchanged.
Exact duplicate passages share a result group.
Duplicate citations do not establish independent corroboration.

The retrieval score measures lexical relevance.
It does not measure truth, engineering compliance or model confidence.
An empty result means the query found no matching passage.
It does not prove that the original documents lack the requested fact.

Citation coverage counts spans referenced by saved records.
It does not measure extraction recall or engineering completeness.
Lineage edges represent stored references.
They do not establish that a cited passage supports a model claim.

## Revision comparison and export

The diff reads stored snapshots from the same project.
It preserves before/after values and links affected records to their source references.
Sensitive trace bodies and image payloads stay outside the diff response.

The dossier includes pending claims, correction history, source hashes and unresolved conditions.
A deterministic hash identifies its content.
The hash does not certify engineering correctness or authorize release.
The separate release workflow still checks current role approvals and gate conditions.

## MCP access

Run the existing MCP server with a scoped project token:

```bash
PYTHONPATH=track_2b/src .venv/bin/python -m tenderproof.mcp_server
```

Set `TENDERPROOF_API_URL` and `TENDERPROOF_MCP_TOKEN` in the calling process environment.
Keep credentials outside source files and prompts.

| MCP tool | Action |
| --- | --- |
| `inspect_review_queue` | Read issues, coverage and lineage |
| `search_evidence` | Retrieve bounded source passages |
| `compare_package_revisions` | Compare two exact snapshot hashes |
| `export_review_dossier` | Read the draft evidence packet |

The tools use authenticated GET requests.
They expose no filesystem paths, arbitrary URLs, shell execution or approval overrides.
The API remains the authorization boundary.
