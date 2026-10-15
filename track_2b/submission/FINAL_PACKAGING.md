# Final local packaging and hand-in

The rendered assets are in `output/`; the required report is also directly under `track_2b/SwissChivers_Report.pdf`. `ARTIFACT_MANIFEST.json` identifies final hashes. Preserve that report location and the `track_2b/` directory in the public repository.

## Required submission

1. Public repository made from the Hack Apertus template, containing the current application, root `make run`, setup instructions, licences, report source and `track_2b/SwissChivers_Report.pdf`. Other template track directories are removed.
2. Upload the six-page report PDF through the official Track 2B form.
3. Record slides 1–8 using `demo.md`, then paste the accessible prototype video URL. Its duration must remain at most 120 seconds. The supporting deck is optional. `TenderProof_Slides.html` is the self-contained speaking deck; `TenderProof_Slides.pdf` is its ten-page export. The existing TTS video is rehearsal material.
4. Fill real first/last name, registered email, team-member names and Swiss-student-team status in `FORM_FIELDS.md`. Do not invent these fields. Review event terms and submit once.

The website deadline is 16 October 2026 at 12:00 CEST / 15:30 IST. The official form is https://hackapertus.ch/online-hack/submissions. Devpost is not the hand-in destination.

## Publication boundary

Exclude `.env`, `.runtime/`, `.venv/`, `node_modules/`, build caches, raw full-document traces, original third-party PDFs, model weights, private deployment identifiers and private task plans. Include complete source-fetch URLs/hashes, the separately labeled assistant QA reference and public verification summaries. Documentation does not grant rights to third-party originals.

Public repository contents must match the reviewed source archive. Recheck hashes after publication and open the report and video URL without authentication. A local build or draft URL is not proof of public access. No form-submission confirmation is claimed unless the actual submission succeeds.

## Rebuilding artifacts

Use `submission/.build/venv` for artifact Python, the project's `.venv` for application work, and the bundled Node artifact runtime. `REAL_SOURCE_EVIDENCE.json` permits rendering only after source, raw-inference and actual-capture checks.

Run the deck builder with `CODEX_ARTIFACT_RUNTIME`, `RUNTIME_NODE_MODULES`, `CODEX_PRESENTATIONS_SKILL` and `TENDERPROOF_SUBMISSION_DIR` set to installed paths. It checks package integrity, geometry, fonts, native tables and first-party import. Then run `source/build_pdfs.py` for report/deck PDFs. Run `source/build_demo_video.py` for the recorded-state walkthrough and `source/check_video.py` for media inspection. Re-review every changed page/slide/scene and refresh hashes after rebuilding.

To rebuild the speaking HTML deck, run `python3 track_2b/submission/source/build_frontend_slides.py`. It checks the two actual capture hashes, embeds fonts and screenshots, and copies exact quoted script paragraphs into notes. The PDF is a Chromium print export using the deck’s embedded 16:9 print styles. Recheck every page after editing.
