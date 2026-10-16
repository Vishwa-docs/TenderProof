# Final packaging and hand-in

## Required submission

1. Use https://github.com/Vishwa-docs/TenderProof as the public repository URL.
2. Upload `track_2b/SwissChivers_Report.pdf` through the official Track 2B form.
3. Record the application with `demo.md`. Keep the video below 120 seconds.
4. Upload the recording. Test its URL without signing in.
5. Add the video URL and team-member names to the report metadata.
6. Fill the remaining personal fields in `FORM_FIELDS.md`.
7. Review the event terms and submit once.

The official portal is https://hackapertus.ch/online-hack/submissions.
The deadline is **16 October 2026, 12:00 CEST / 15:30 IST**.
The slides support the GitHub README. The final recording shows the application.

## Publication boundary

Exclude credentials, runtime archives, virtual environments, model weights and private deployment identifiers.
Keep original third-party PDFs outside the public repository.
Publish source URLs, hashes, fetch instructions and labeled QA references.
The source catalog does not grant redistribution rights to the original documents.

`ARTIFACT_MANIFEST.json` records current deliverable hashes.
Public archive verification compares each repository file with the reviewed export.
A final video URL still requires anonymous playback verification.
No submission confirmation exists until the official form succeeds.

## Rebuild the report

Install the PDF builder dependencies in an artifact virtual environment:

```bash
python3 -m venv .venv-artifacts
.venv-artifacts/bin/pip install reportlab==4.4.9 pypdf==6.10.0
.venv-artifacts/bin/python track_2b/submission/source/build_report.py
```

The builder reads the report Markdown and its diagrams.
Review every rendered page after changes. Keep the report within the official page limit.

## Rebuild the supporting slides

```bash
python3 track_2b/submission/source/build_frontend_slides.py
```

The builder embeds the registered captures and local fonts.
Browser print exports the matching PDF at 16:9.
The deck has independent optional notes. It does not read the video script.
Review all slides after changes. Refresh hashes before publication.
