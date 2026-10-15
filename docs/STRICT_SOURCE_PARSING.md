# Actual PDF parser revalidation

Checked 2026-10-15. All five authentic original PDFs have strict-success coverage evidence across **two execution contexts**: four isolated offline reparses and the separately completed actual API parse of the full tender. This is not a claim that all five passed in one isolated run. No language-model inference, database write or duplicate full-tender parse was performed during this verification. Local Docling layout/OCR models were used for the isolated reparses.

| Original source | Pages | Spans | Retained characters | Largest span | Verification context |
| --- | ---: | ---: | ---: | ---: | --- |
| gpa-op34276.pdf | 9 | 329 | 36,349 | 1,783 | Isolated offline reparse |
| gpa-e004-rev10.pdf | 20 | 384 | 42,555 | 7,539 | Isolated offline reparse |
| gpa-07025-bid-abstract.pdf | 5 | 104 | 22,477 | 4,754 | Isolated offline reparse |
| gpa-07025-amendments.pdf | 4 | 105 | 7,744 | 550 | Isolated offline reparse |
| gpa-07025-full-ifb-amendment-i.pdf | 57 | 1,214 | 233,182 | 14,783 | Actual API upload, saved snapshot |

Each result reports Docling `success`, zero conversion errors, exact converted-page coverage, retained source spans on every expected page, and an original-file SHA-256 matching the catalog. Saved JSON hashes and metrics were independently recomputed. All five saved span arrays exactly match the corresponding document arrays in the actual five-source API snapshot. The total is **95 attachment pages, 2,136 spans and 342,307 retained characters**. Specification, amendment and invitation content overlaps; 95 is not a unique-page count.

## Preserved isolated-run failure

The isolated `tenderproof:documents` batch completed the first four files. Docker then recorded `oom` and `die` with exit code 137 for `tenderproof-source-revalidation` at Unix timestamp `1792056953`. It was processing the full 57-page tender. That attempt produced no complete fifth parsed artifact and is retained as a failure. The application was also parsing the full tender in the 8 GiB Docker VM. Heavy parses should be serialized.

The planned fresh-process retry was not run: the parent API upload completed successfully, so its real saved result supplied the separately labeled fifth verification. No source or failure was relabeled to imply a successful five-file isolated run.

The isolated image was `sha256:c484c461a1261c8d84e0a753a8c2e73058a13304c07ef1b2a82bf2069185f424`, with Docling 2.139.0, docling-core 2.101.1, PDFium 5.14.0 and RapidOCR 3.10.0. Docker inspection recorded network mode `none`, read-only parser and original-source mounts, and a dedicated writable validation directory. The validation container initially had two CPUs, later four, with a 6 GiB memory cap; application containers were not stopped by this check.

## Full-tender native text and window checks

The actual API project snapshot is `.runtime/real-project-five-before-restart.json`, SHA-256 `6365646654ce770059152e625a74d990d3e7d07b1d5e467aa2a1426437e1fcd0`. Its full-tender document matches original SHA-256 `a101432f314d0839c3d114779f42b03e7b08766476a78eb817074ea7d1f01d10`. PDFium independently read **1,980 nonempty embedded-text lines** over 57 pages: zero lines were missing from retained source text on the same page after whitespace/case normalization. This checks content presence; repeated identical lines do not establish positional multiplicity.

The read-only requirement planner checked at 2026-10-15 09:44 UTC produced six windows. Flattening their ranges exactly reproduced all 1,214 original spans in their saved order, with no span splitting or text truncation:

| Window | Spans | Raw characters | Serialized source characters |
| --- | ---: | ---: | ---: |
| 1 | 670 | 44,711 | 54,347 |
| 2 | 338 | 44,444 | 49,625 |
| 3 | 4 | 45,948 | 46,345 |
| 4 | 121 | 47,892 | 49,885 |
| 5 | 78 | 47,591 | 49,454 |
| 6 | 3 | 2,596 | 2,673 |

All windows fit the checked 48,000-character raw and 56,000-character serialized-source bounds. PDFium supplements are appended after Docling spans, so later windows can revisit earlier PDF page numbers. Original saved span order is preserved; page numbers are not globally sorted. Six windows would plan 24 role calls, but none were executed here. Cross-window references and global consistency remain engineering review work.

Supplier and evidence planning on this full 233,182-character document correctly abstained before inference because those purposes require a complete single pass below their 100,000-character limit. The complete five-page bid abstract remains a separate source for bidder extraction. No selected-page substitute or inferred commercial offer was created.

## Local evidence paths

- `.runtime/quality/revalidated/summary.json` and `combined-summary.json`: combined status, metrics and explicit execution contexts.
- `.runtime/quality/revalidated/*.parsed.json` and `*.summary.json`: complete source records and per-source checks. The fifth JSON is the unchanged document object serialized from the actual API snapshot.
- `.runtime/quality/revalidated/summary-attempt-1.json`, `summary-before-termination.json`, `container-attempt-1.log` and `container-attempt-1-events.json`: failed isolated attempt and Docker OOM evidence.
- `.runtime/quality/revalidated/container-runtime.json` and `resource-change.json`: isolation, image and resource records.
- `.runtime/quality/revalidated/verify_integrated_full.py` and `aggregate_integrated.py`: read-only artifact verification and aggregation scripts.
- `.runtime/real-project-five-before-restart.json`: actual integrated five-source API snapshot.

These runtime files are ignored local analysis evidence. The original third-party PDFs and complete extracted text are not relicensed or added to a public dataset. Source URLs and rights limits are recorded in [the source catalog](REAL_DATA_SOURCES.md); page identity, real prices, amendments and evidence gaps are discussed in [the package review](REAL_PACKAGE_REVIEW.md).

Strict parser success establishes conversion status and coverage. It does not establish perfect OCR, extracted image content, expert approval, supplier compliance or passing test measurements. Scanned content still needs visual source review. No matching unit FAT, serial-number nameplate, approved drawing revision or actual drawing-approval date was established by this check.
