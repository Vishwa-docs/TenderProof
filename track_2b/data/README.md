# Source catalog

`sources.json` describes five authentic GPA-070-25 PDFs: four Guam Power Authority / Open GovGuam attachments and the GPA-authored full tender with Amendment I hosted by the Pacific Power Association. The selected analysis scope is OP34276 item 2, the 750 kVA transformer; the separate 300 kVA item is excluded. Download originals with `make sources`, then explicitly upload them with `make ingest` or the workbench.

The team-authored catalog selection and descriptive metadata are provided by SwissChivers (2026) under [CDLA-Permissive-2.0](../../LICENSES/CDLA-Permissive-2.0.txt). The catalog is not a licensed copy of the original documents and contains no model evaluation results.

Original PDFs remain third-party works. No redistribution permission has been established, and the project grants no rights in their contents. They are downloaded into ignored `.runtime/sources/`, with original URL, actual byte length and SHA-256 recorded in a local manifest. Do not publish originals, extracted text or screenshots as a team-licensed dataset without establishing the applicable rights. See [source attribution and limitations](../../docs/REAL_DATA_SOURCES.md) and [licensing scope](../../NOTICE.md).

The four-page portal attachment labeled “IFB Issuance” contains amendments and an invitation. The separate 57-page PPA file contains the original 55-page tender plus two Amendment I pages; official Amendments II and III remain separately relevant. Together the five files contain 95 attachment pages with duplicated specification, invitation and amendment content; this is not 95 unique pages. The source set contains no verified unit-specific FAT report or serial-number nameplate evidence.

`evaluation/gpa-source-facts.json` is an assistant source-checked QA reference, not expert validated and never an inference input. It distinguishes historical Mac-parse locators from hash-bound current-runtime locators and marks OCR ambiguities explicitly; original source values are not rewritten to match OCR.
