# Track 2B submission requirements

Verified 15 October 2026 against the official website, the visible Track 2B form, the official template, and Devpost. Recheck the live form before submission. No external form has been filled or submitted by this project.

**Deadline: 16 October 2026, 12:00 CEST (10:00 UTC; 15:30 IST). No extensions. Submit once per project at [the official portal](https://hackapertus.ch/online-hack/submissions). Devpost explicitly directs submissions to this website; a Devpost project entry is not a substitute.**

## Official sources

| Source | What it establishes | Accessed |
| --- | --- | --- |
| [Submission portal](https://hackapertus.ch/online-hack/submissions), select “Track 2B - Own Project” | Exact form fields, required uploads, one entry per project, deadline | 2026-10-15 |
| [Official Track 2B README](https://github.com/HackApertus/project-template/blob/main/track_2b/README.md) ([raw text](https://raw.githubusercontent.com/HackApertus/project-template/main/track_2b/README.md)) | Deliverables, architecture, repository, Docker, data limit, evaluation | 2026-10-15 |
| [Devpost event](https://hackapertus.devpost.com) | Website-only submission route, team size 1-5, judging criteria | 2026-10-15 |
| [Devpost rules](https://hackapertus.devpost.com/rules) | Eligibility and schedule | 2026-10-15 |
| [Terms and Conditions](https://hackapertus.ch/terms-and-conditions), dated 2026-08-28 | Open-source licences, dataset provenance, submission warranties | 2026-10-15 |

## Exact visible form fields

An asterisk below records the form's required marker. Dropdown choices were opened and read without entering participant data.

| Field | Required | Prepared value / dependency |
| --- | --- | --- |
| Select track/challenge | Yes | Track 2B - Own Project |
| First name | Yes | Human input |
| Last name | Yes | Human input |
| Email (used for Devpost sign-up) | Yes | Human input; use the registered email |
| GitHub username | Yes | Human input |
| Hugging Face username | No | Human input or blank |
| Team name | Yes | SwissChivers, supplied by participant |
| Team members | Yes | Human input; list actual contributors |
| Project name | Yes | TenderProof |
| Swiss student team | Yes | Yes / No; human must answer accurately |
| Model | Yes | Choices: 8B v1.5; 70B v1.5; 8B + 70B v1.5. Select only the model actually run |
| Technical report (PDF, max. 6 pages) | Yes | Local PDF in `submission/output/`; final team filename must be set |
| Hugging Face dataset URL (optional) | No | Blank unless an actual public dataset has been published |
| GitHub repository URL | Yes | Actual public project repository URL; not the upstream template |
| Demo video URL (max. 2 min) | Yes | Actual publicly accessible or judge-accessible video URL after recording/upload |
| Your message (optional) | No | Copy-ready text in `submission/FORM_FIELDS.md` |
| Accept Terms and Conditions | Yes | Human review and acceptance at submission |

The form does **not** request a deck, hosted application URL, logo, tagline, screenshot, or Devpost project URL. The deck is a supporting artifact requested by the project owner.

## Repository and deliverable checklist

- [ ] Confirm eligibility: 18+, allowed residence, true team size 1-5, registered participant details.
- [ ] Confirm this is a new project started during the event (1-16 October 2026); do not infer provenance from file timestamps.
- [ ] Use Apertus for the submitted solution. Document any supporting model's role and preserve actual inference evidence. Application and demonstration data must be real, per participant instruction.
- [ ] Demonstrate deployment in at least one mandatory architecture: on-premise, air-gapped, or sovereign Swiss cloud. Current target is on-premise; do not claim a Swiss deployment without residency/jurisdiction evidence.
- [ ] Preserve the `track_2b/` directory name and position. Remove the other track directories from the final submission repository. Include all prerequisite template files, definitions, inputs and outputs.
- [ ] Create the team's own PUBLIC repository from the template and submit its real URL. Current upstream origin alone is insufficient.
- [ ] Run the Docker container with `make run` from the repository root and complete an end-to-end judge flow on a clean setup.
- [ ] Update `track_2b/technical_report.md`; place the final PDF in `track_2b/` as `TeamName_Report.pdf`. The confirmed team name gives `SwissChivers_Report.pdf`.
- [ ] Keep report content at most six pages excluding references. The official Track 2B template permits six content pages plus references.
- [ ] Record a prototype demo no longer than 120 seconds; verify duration and audio, publish an accessible URL, test the link without the creator's session.
- [ ] Keep `track_2b/data/` at or below 100 MB.
- [ ] Apply Apache-2.0 to code/weights, CC-BY-4.0 to team-authored documentation/non-code output, CDLA-Permissive-2.0 to submitted datasets; retain third-party rights/notices and verify the right to redistribute each source item.
- [ ] Confirm all contributors can grant the required licences and the submission contains no confidential or unlicensed material.
- [ ] Replace pending evidence in the report/deck with actual commands, model identity, run metadata and results; preserve honest “not run” entries where appropriate.
- [ ] Complete every required form field, review the Terms and Conditions, and submit once before the deadline. Save the actual confirmation receipt.

## Optional Hugging Face dataset

This is optional for Track 2B. Do not fabricate a dataset link or model response. If publishing: clone [the official dataset template](https://huggingface.co/datasets/HackApertus/online_hack_template); complete the dataset card; include real evaluation cases, corresponding actual model responses, and per-case metadata/licensing where relevant; make the dataset PUBLIC; submit its URL. Data must be created by the team or publishable with permission. Human-subject data requires suitable consent, an included consent template, explicit AI use permission and anonymisation under the organizer's rules.

## Judging criteria

The official template uses five dimensions scored 0-5: purposeful use of AI; technical rigour; value, cost and scalability; sovereign deployability; implementation feasibility. Evidence should connect each claim to a reproducible artifact. Savings, live-model quality, production deployments and customer traction remain unclaimed unless measured.
