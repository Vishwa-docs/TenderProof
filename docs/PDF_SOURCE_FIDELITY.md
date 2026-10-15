# Actual purchase-order PDF fidelity check

Checked 15 October 2026 against the complete nine-page [GPA purchase order OP34276](https://go.opengovguam.com/uploads/ggbids/packet_1765520985_OP%2034276.pdf), downloaded from its original public URL. This is a parser/content-preservation check, not an Apertus evaluation. The original PDF and extracted text remain in ignored runtime storage; no third-party PDF is relicensed or added to the public dataset.

Original SHA-256: `da91f24252a7131e06a9861e56593a66146173bf0e8d0764f2194e6e63b8c551`.

## Measured result

| Parse | Source spans | Sum of span text characters | Pages |
| --- | ---: | ---: | ---: |
| Existing macOS Docling output | 654 | 27,831 | 9 |
| Fresh offline Docker Docling output | 320 | 33,637 | 9 |
| Docker output plus embedded-text supplement | 329 | 36,349 | 9 |

Fewer spans did not mean less text: different layout/table reconstruction produced larger spans and some repeated text in Docker. The selected 750 kVA item and its unit price were present in the Docker parse. A comparison with the PDF's embedded text found omitted issuer/telephone text and lost list/clause labels, including labels on page 6. The associated underlying engineering phrases were generally present. PDF pages 4 and 6 were rendered and visually inspected against those findings.

The parser now retains each non-empty native text line absent from the same page's Docling output, grouped into one supplemental span per affected page. The comparison normalizes whitespace and case only; it preserves inequality signs, punctuation, units and clause labels. Supplemental spans retain the original page, have `bbox=null`, use a stable `<document-id>:native:<page>` ID, and are marked `source_kind=pdf_native_text`. Existing Docling source spans and their coordinates remain intact.

For this actual PDF, the supplement added nine page spans and 2,712 characters. A page-by-page assertion verified that **every embedded PDF text line** appears in the combined output after whitespace normalization. The same supplement was executed successfully in `tenderproof:documents` with networking disabled and read-only source/code mounts: 329 spans, 36,349 characters, nine pages with embedded text. No application database was modified.

This does not prove correct OCR, table cell relationships, handwriting recognition, or completeness of text that exists only in images. Scanned PDFs still depend on Docling OCR and visual review. The workbench must preserve original-page review; a source citation proves provenance, not correct interpretation. No claim of zero-loss extraction across the four-document package is made.

## Reproduction evidence

Local files from this check, all ignored by Git:

- `.runtime/sources/gpa-op34276.pdf` — complete original.
- `.runtime/sources/gpa-op34276.parsed.json` — prior macOS output.
- `.runtime/quality/po-docker-parsed.json` — fresh Docker output, before supplement.
- `.runtime/quality/po-docker-parse.log` — parser log.
- `.runtime/quality/po-docker-supplemented.json` — combined output.
- `.runtime/quality/po-page4.png`, `po-page6.png` — rendered pages inspected.

The baseline Docker command ran the existing `tenderproof:documents` image with `--network none`, mounted `.runtime/sources` read-only at `/sources`, and called `parse_document` on the complete original. No model endpoint was contacted. The follow-up container mounted the current `track_2b/src/tenderproof` read-only and called `_supplement_pdf_text` on that saved baseline plus original bytes; its measured result matched macOS execution of the same supplement.

The automated regression `test_native_pdf_supplement_preserves_omitted_clauses_operators_and_page_identity` separately checks a constructed edge case: text on another page cannot suppress a missing line, `<=` is not collapsed into `>=`, whitespace-only variants are not duplicated, and a repeated merge does not append duplicate spans. This isolated software test is not evidence about real model quality.
