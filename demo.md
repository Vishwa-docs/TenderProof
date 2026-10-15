# TenderProof — recording script

**Target: 1 minute 55 seconds. Hard limit: 2 minutes.**

Open `TenderProof_Slides.html` from the submission folder. Record slides 1–8 in full screen. Press F for full screen and R to hide the controls. Use Right Arrow to advance. Read only the quoted paragraphs, exactly as written. Slide cues and timings are not spoken. Slides 9–10 are optional appendices and stay out of the video.

The screenshots show the real recorded application state. Do not start a new model run during recording: the recorded full-tender run took 427 seconds. Keep every proposal pending.

## 1 · The problem · 0:00–0:14

Show: title slide.

> TenderProof connects what an infrastructure contractor promises, buys, and accepts. It gives engineering and procurement teams one place to review the evidence before releasing a purchase or shipment.

## 2 · The real package · 0:14–0:27

Show: real purchase and source documents.

> This is a real Guam Power Authority purchase: three seven-hundred-and-fifty kVA transformers. We ingested five complete public documents, including the tender, bid abstract, amendments, and purchase order.

Pronunciation note, not spoken: say “kVA” as “kay vee ay.”

## 3 · The workflow · 0:27–0:40

Show: requirements, supplier comparison, acceptance and change control.

> Apertus proposes requirements and supplier facts. Reviewers open the original source, check the interpretation, and approve the exact package revision. Changes invalidate earlier decisions.

## 4 · The error · 0:40–0:57

Show: the model's lot-total error and the correct unit price.

> Here is a real extraction error. The model used a three-unit total as the unit price. The corrected unit price is thirty-seven thousand, one hundred and five dollars, fifty cents.

## 5 · The correction · 0:57–1:10

Show: actual correction history with its page-four citation.

> This correction cites purchase-order page four. The application keeps the original model value, corrected amount, reviewer identity, and reason. The proposal remains pending.

## 6 · The release gate · 1:10–1:26

Show: actual extraction warnings and missing factory evidence.

> Missing evidence stops the workflow. This package has no completed factory acceptance report. The system also records a truncated audit and capped output. Both release gates remain blocked.

## 7 · The engineering · 1:26–1:39

Show: on-premise architecture and measured software checks.

> Apertus runs on our GPU. PostgreSQL keeps versioned records, Temporal coordinates extraction, and Z3 checks encoded commitments. The build passes three hundred sixty-nine software tests.

## 8 · The business · 1:39–1:55

Show: transformer procurement first, then the expansion path.

> We start with transformer procurement for energy contractors. Our next step is a design partner pilot, measuring missed obligations and review effort. Then we expand into enterprise purchasing and additional equipment categories. TenderProof. Evidence before release.

---

## Before uploading — not spoken

- Rehearse once and check the recorded duration. Aim to finish by 1:55.
- Use a clear speaking pace and short pauses between slides. Do not read the headings or instructions.
- The correction shown was entered by an AI assistant through the audited flow and still awaits qualified review. Do not call it an expert approval.
- Software test counts do not measure model accuracy. No purchase, shipment, revenue or customer partnership is claimed.
- The model endpoint is stopped after recording. “Runs on our GPU” describes the tested deployment architecture; it does not promise an always-online endpoint.
- Upload your final recording, then paste its accessible URL into the official Track 2B form. The generated narration draft is optional rehearsal material.
