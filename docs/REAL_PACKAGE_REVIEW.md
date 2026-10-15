# Source review: GPA-070-25 / OP34276

Reviewed 2026-10-15. This is an assistant source check against authentic downloaded originals, not expert validation, a supplier submission, or an Apertus extraction result. Page numbers below are one-based PDF pages. The selected scope is purchase-order item 2: three 750 kVA transformers. The same order also contains a separate 300 kVA configuration; its values must not be merged into this scope.

Sources are cataloged in `track_2b/data/sources.json`. Originals stay in ignored `.runtime/sources` because no redistribution permission was established. Public availability does not establish a permissive license. The QA manifest under `track_2b/data/evaluation/` is separate from inference inputs.

## Checked originals

| Source | Original inspected | SHA-256 |
| --- | --- | --- |
| [OP34276](https://go.opengovguam.com/uploads/ggbids/packet_1765520985_OP%2034276.pdf) | 9 pages; complete text and page overview; detailed visual checks of pages 4, 5, 6 and 9 | `da91f24252a7131e06a9861e56593a66146173bf0e8d0764f2194e6e63b8c551` |
| [E-004 Rev. 10](https://go.opengovguam.com/app/webroot/userfiles/files/Spec%20E-004%20Revision%2010%20-%20Three%20Phase%20Pad%20Mounted%20Distribution%20Transformer%282%29.pdf) | 20 scanned pages; full page overview; detailed visual checks of pages 5-8, 11, 18 and 20 | `d21a10dd0d4b31ad85c1bfa1fa07d577b0beeccd24774d109cef94129a05c414` |

The remaining originals were also inspected:

| Source | Original inspected | SHA-256 |
| --- | --- | --- |
| [Bid abstract](https://go.opengovguam.com/uploads/ggbids/packet_1765520985_GPA-070-25%20Bid%20Abstract.pdf) | 5 scanned PDF pages: four numbered bid forms and one attendance page; all rendered, price cells enlarged | `ea238725bcf796aa9df08ba0d7cffacd105943a0782fd05b736f9cc5ed9a4b8b` |
| [Issuance / amendments attachment](https://go.opengovguam.com/uploads/ggbids/packet_1765520985_GPA-070-25%20IFB%20Issuance.pdf) | 4 PDF pages; all rendered and compared with embedded text | `32b395fcaa2ea49d054f63b38f6f53508a4dba32be5f0559f51e94b530ece22b` |
| [Full tender with Amendment I](https://www.ppa.org.fj/wp-content/uploads/2025/08/220825GPA-GPA-070-25-with-Amendment-I.pdf) | 57 PDF pages, 1,668,269 bytes; all rendered, full page overview, detailed identity/item/revision/end-page checks | `a101432f314d0839c3d114779f42b03e7b08766476a78eb817074ea7d1f01d10` |

The procurement portal identifies the related order, abstract and issuance attachment: [official procurement record](https://go.opengovguam.com/tenders/tender_details/gpa/GPA-070-25). Five source files have now been rendered and inspected. The newly located PPA mirror contains the original 55-page tender plus two Amendment I pages. The government portal attachment remains a separate four-page compilation.

## Full tender identity, pagination and embedded revision

The [57-page PPA-hosted GPA tender](https://www.ppa.org.fj/wp-content/uploads/2025/08/220825GPA-GPA-070-25-with-Amendment-I.pdf) now establishes full tender availability. PDF pages 1-2 contain Amendment I and its replacement invitation; PDF pages 3-57 carry original printed pages 1-55 without a numbering gap. The final PDF page visibly says 55 of 55. This is a GPA-authored procurement document mirrored by the Pacific Power Association, not a supplier response. Its original envelope identifier, **41905CA8-A9DB-45C2-9638-CA07AD868CAC**, matches the [government-issued invitation](https://go.opengovguam.com/uploads/ggbids/packet_1765520985_GPA-070-25%20IFB%20Issuance.pdf), PDF page 4. Amendment I has the separate C4BC10C7-4995-47EE-AD40-90009DE8D27A identifier. These are visible content matches, not cryptographic signature validation.

| Full PDF page(s) | Printed page(s) | Content |
| --- | --- | --- |
| 1-2 | Amendment I; replacement 3a of 55 | September 9 bid-opening revision |
| 3-57 | 1-55 of 55 | Original tender; original page = PDF page minus 2 |
| 5 | 3 of 55 | Original invitation and drawing-approval-relative delivery |
| 6-7 | 4-5 of 55 | Separate 300 kVA item 1, quantity four |
| 8-9 | 6-7 of 55 | Selected 750 kVA item 2, quantity three |
| 10-29 | 8-27 of 55; E-004 pages 1-20 | Embedded E-004 Revision 10, dated July 29, 2022 |
| 29 | 27 of 55; E-004 page 20 | Blank Appendix A, including flip-top row 21 |
| 57 | 55 of 55 | Final original solicitation-instructions page |

The embedded specification is **Revision 10 dated July 29, 2022**, not a 2005 revision. Every embedded specification page was compared with the standalone E-004 file: all 20 page image sets have identical dimensions, encoded image-stream hashes, filters and JBIG2 global data. This establishes the same scanned specification content; the full tender adds outer pagination and its envelope header. It does not make the two PDF files byte-identical. The QA manifest records the page correspondence and image-set hashes.

Item 2 on PDF page 8 matches OP34276's 750 kVA quantity, voltages, BIL, insulation class and item index. Its price cells and compliance responses are blank. Manufacturer/model and bidder delivery response fields on page 9 are blank. The requirement still starts 24 weeks after GPA-approved drawings; a separate blank bidder field asks for time after purchase-order receipt and supplies no actual period or approval date. This uncompleted form cannot establish an offer, alternative delivery baseline, measured performance or manufactured-unit identity.

Amendment I is the only amendment included in this full file. Later official Amendments II and III remain necessary: flip-top clarification and the September 16 opening supersede relevant earlier information. Five downloaded files total **95 attachment pages**, with duplicated specification/amendment material; this is not a count of 95 unique pages. No completed FAT, serial-number nameplate or approved unit drawing was found in the full tender.

## Selected item: source facts

| Fact | Verified value | Source location |
| --- | --- | --- |
| Issuer / procurement / contract | Guam Power Authority / GPA-070-25 / C-070-25 | OP pages 1 and 4, header |
| Purchase-order identifier and date | Printed order number 34276; date 2025-10-13 | OP pages 1 and 4, header |
| Awarded vendor | R&D Marketing and Lypco International | OP page 4, vendor block |
| Selected equipment | Item 2, 750 kVA, three-phase pad-mounted transformer | OP page 4 |
| Quantity / unit price / line amount | 3 EA / USD 37,105.5000 / USD 111,316.50 | OP page 4, item row |
| Order total | USD 201,964.10; covers both configurations | OP page 9 total; 300 kVA line on page 1 |
| Manufacturer / model | Eaglerise Electric & Electronic (China) Co. / **ZGSLB-750/13.8-0.208** | OP page 6 |
| Electrical configuration | Primary 13.8 kV; secondary 120/208 V; insulation 15 kV; BIL 95 kV | OP page 4, A.1 |
| Feed and enclosure | Dead-front, three-bushing radial feed; specified parts in type 304L stainless steel | OP page 4, A.1-A.2 |
| Incorporated specification / item index | E-004 Revision 10 / E4075013802020B-3 | OP page 4 |
| Specification date | July 29, 2022 | E-004 header on all pages |
| Applicable table row | 750 kVA at 208Y/120 V: minimum impedance 5.75%, ten-hole secondary spade | E-004 page 8, Table 1; these are requirements, not measured values |

Arithmetic check only: `3 × 37,105.50 = 111,316.50`; the separate 300 kVA line is `4 × 22,661.90 = 90,647.60`; their sum is `201,964.10`. These calculations corroborate the printed amounts, not technical compliance or the economics of an alternative supplier. The awarded vendor and manufacturer are distinct entities. The model contains a hyphen after ZGSLB; dropping it is a catalog transcription issue, not a source ambiguity. [OP original](https://go.opengovguam.com/uploads/ggbids/packet_1765520985_OP%2034276.pdf).

## Delivery basis and submittal obligations

The order specifies 24 weeks **after GPA approval of drawings**, repeated in the header including page 4. It does not supply the actual drawing-approval date. A calendar due date, current lateness, project epoch, or accepted extension cannot therefore be calculated from this package alone. The order date, signed acknowledgment date, signature date and later copy stamp are not drawing-approval evidence. Page 7 permits consideration of supported extension requests without guaranteeing approval. [OP original, pages 4 and 7](https://go.opengovguam.com/uploads/ggbids/packet_1765520985_OP%2034276.pdf).

E-004 page 5, sections 4.3-4.5, requires final shop drawings for GPA review, allows two weeks for review, and treats returned approved drawings as authorization to proceed. Its page 6, sections 5.1-5.3, requires certified tests and reports before shipment, including independently certified loss data. These clauses establish obligations; they do not establish that reports exist or passed. [E-004 original, pages 5-6](https://go.opengovguam.com/app/webroot/userfiles/files/Spec%20E-004%20Revision%2010%20-%20Three%20Phase%20Pad%20Mounted%20Distribution%20Transformer%282%29.pdf).

## Acceptance evidence that remains unavailable

The reviewed originals do not contain a unit-specific completed laboratory/FAT report, test date, inspector witness record, measured losses, manufactured-unit serial number, serial-number nameplate photograph, approved final shop drawing, drawing revision history, or drawing-approval date. E-004 Appendix A on page 20 is an **uncompleted template**, not this supplier's completed response. OP page 5 requires reports for each delivered transformer and serial identifiers on delivery records. Those requirements cannot populate actual evidence records. No unit-specific release, revision match, test result, or compliance conclusion follows from them. [OP pages 5-6](https://go.opengovguam.com/uploads/ggbids/packet_1765520985_OP%2034276.pdf), [E-004 pages 6 and 20](https://go.opengovguam.com/app/webroot/userfiles/files/Spec%20E-004%20Revision%2010%20-%20Three%20Phase%20Pad%20Mounted%20Distribution%20Transformer%282%29.pdf).

E-004 Revision 10 is an identified specification revision. It is not evidence of the purchased unit's design revision. Do not create an invented wrong-revision FAT case. Any future report must be checked against its actual unit identity, scope, configuration and approvals.

## Parsed purchase-order quality check

Compared `.runtime/sources/gpa-op34276.parsed.json` (SHA-256 `99c3899e8d81f5df418bb009a1d399f0f80e37bc1604888e173e35235382b984`) with the original, bound by the matching PDF SHA-256. It contains 654 spans. No numeric OCR error was observed in the checked 750 kVA amount, quantity, model, voltage, BIL, item index, delivery period, or order-total fields. This is a targeted check, not a claim that every character is correct.

| Observed parsing issue | Source comparison | Consequence |
| --- | --- | --- |
| Duplicate/misassigned header text | On page 4, span 256 repeats vendor contact text in the location of the Authority label; span 257 holds 3109. Similar duplication occurs on pages 1-8. | Do not treat duplicate spans as corroboration or parse contacts as the Authority value. |
| Manufacturer split across spans | Page 6 spans 435-436 split the manufacturer after `(China)` and attach `Co.` to the model label. | Recover the manufacturer across adjacent source spans; keep it separate from the vendor. |
| Image placeholders | 50 spans contain Docling's unavailable-image marker rather than an image description. Original pages visibly contain logos and signatures. | A placeholder cannot establish a signature, nameplate, or visual inspection. Open the original. |
| Handwriting noise | Page 2 span 144 is `9P`; similar isolated characters occur near handwritten marks. | Do not turn handwriting artifacts into engineering values or evidence identifiers. |
| Parser metadata | Revision is `unreviewed`, authority `unreviewed_source`, language `und`. | These are ingestion defaults; they are not authenticated source revision, issuer or language determinations. |

Do not edit the raw parsed artifact to hide these issues. The manifest records the source-checked reference values and exact span IDs separately. The generic E-004 specification allows two secondary-voltage choices; the selected PO line resolves the scope to 120/208 V. Loss submittal labels are not actual guaranteed or measured loss numbers.

## Current-runtime QA locator binding

The QA manifest now distinguishes the historical 654-span Mac purchase-order parse above from the current **329-span** runtime parse (parsed JSON SHA-256 `43ce41a81f40bcd016b10189db00908f4f5bceb2cb59240215a8d96bd4a00cdf`). The old IDs are preserved under `historical_parsed_locator`, bound only to their original artifact; they must not be looked up in the current parse. All 35 fact records now have explicitly scoped current-runtime locators. Each of 39 page locators and 52 span references was checked against its named parsed-artifact hash, source PDF hash and actual PDF page; all five source span arrays match `.runtime/real-project-five-before-restart.json`. Source fact values, classifications and acceptance-evidence gaps were retained. QA remains assistant checked, not expert validated, not inference input and not human approval.

The saved current bid-abstract parse now permits a targeted comparison with the earlier enlarged-page visual readings. Three basic line-item-2 prices do **not** match the original-page QA readings:

| PDF page / bidder | Current span suffix | OCR text | Visually checked QA value, USD |
| --- | --- | --- | --- |
| 3 / Benson Guam | `:35` | `25,000.00` | 25,600.00 |
| 4 / Polyphase | `:58` | `2,25224` | 27,252.26 |
| 5 / JMI Edison | `:83` | `34,a50.00` | 34,250.00 |

The full span prefix is `ea238725bcf796aa9df08ba0`; the matching parsed JSON SHA-256 is `a0cfc90b0379e173dd0216412f6916d2c8eed1bab78571599a5a96f14b3f2eb2`. These are large table spans. The relevant original-page region is the **BASIC / UNIT COST row, LINE ITEM 2 column**; recorded table bounding boxes do not isolate individual cells. Those locators are explicitly partial and require original-page review. R&D's 37,105.50 and Benson's alternate 22,845.00 are present in the current text, but bidder handwriting and blank fields still need visual review. Uncompleted-form observations have page-context-only locators: OCR absence cannot prove a blank field. No source fact was changed to fit an OCR error, no parsed text was corrected, and no uncertain price was approved.

## Authentic amendments and their scope

| PDF page | Date / amendment | Observed effect |
| --- | --- | --- |
| 1 | 2025-09-08 / III | Moves bid opening from 2025-09-09 10:00 to 2025-09-16 09:00, CHamoru Standard Time (ChST). References replacing original page 3a with 3b of 55. |
| 2 | 2025-09-02 / II | Resolves the bidder's sealed-cover versus Appendix A flip-top question. The answer requires the flip-top response **“no”** because a flip-top is not required. |
| 3 | 2025-08-21 / I | Moves bid opening from 2025-08-29 10:00 to 2025-09-09 10:00 ChST. References original page 3 replaced with 3a of 55. |
| 4 | Invitation, original page 3 of 55 | Shows the earlier August 29 deadline and the same 24-week drawing-approval-relative delivery basis. Bidder/award fields are blank. |

This government attachment has four pages, **not** the original 55-page tender. The original tender is now available separately in the 57-page PPA mirror reviewed above. The attachment retains an older invitation page even though later amendments change its bidding deadline. Do not silently prefer the last PDF page as the latest governing date. No inspected amendment changes the transformer rating. Amendment II clarifies the Appendix A response; it does not establish that a supplied unit's cover was inspected. E-004 page 11, section 9.1, specifies a welded sealed tank cover; Appendix A page 20 contains the flip-top yes/no prompt in row 21. The amendment inquiry's Appendix page 27 now maps directly to full-tender PDF page 29 (printed 27 of 55), corresponding to standalone E-004 page 20. [Amendments original](https://go.opengovguam.com/uploads/ggbids/packet_1765520985_GPA-070-25%20IFB%20Issuance.pdf), [E-004 original](https://go.opengovguam.com/app/webroot/userfiles/files/Spec%20E-004%20Revision%2010%20-%20Three%20Phase%20Pad%20Mounted%20Distribution%20Transformer%282%29.pdf).

## Bid abstract: readable prices and important limits

The abstract records 15 invitations issued and four bids received, opening 2025-09-16 at 09:00. The five PDF pages comprise four bid forms (printed internal pages 1-4) and an attendance sheet at PDF page 2. PDF page numbers must therefore be used for source locators. The capacity mapping of abstract line item 2 to 750 kVA comes from OP34276 item 2; the abstract itself labels the columns by item number rather than capacity. These handwritten line-item-2 prices were checked in enlarged original-page images:

| Bidder as written | Basic unit price, USD | Alternate unit price, USD | PDF page |
| --- | --- | --- | --- |
| R&D Marketing | 37,105.50 | Blank | 1 |
| Benson Guam Enterprises Inc. | 25,600.00 | 22,845.00 | 3 |
| Polyphase System Inc. | 27,252.26 | Line-item-2 alternate blank | 4 |
| JMI Edison | 34,250.00 | Blank | 5 |

These are assistant readings of handwritten bid tabulations, not expert-approved commercial offers. The typed awarded purchase order is the stronger source for the selected R&D item and its exact manufacturer/model. Other model/catalog entries remain untranscribed where handwriting could be ambiguous. The abstract does not supply guaranteed losses, completed technical submissions, certified measurements, or a documented TCO evaluation supporting award. Its award-basis checkboxes are unmarked; price differences alone do not explain why an award was made. Do not call the cheapest tabulated amount the compliant winner. [Bid abstract original](https://go.opengovguam.com/uploads/ggbids/packet_1765520985_GPA-070-25%20Bid%20Abstract.pdf).

Source anomaly: the handwritten invitation number on PDF page 5 appears to end **-24**, while the other bid forms show -25 and all show the September 16, 2025 opening. Preserve this discrepancy for review; do not change the original or invent a second procurement. Polyphase's crossed-out alternate entry on PDF page 4 is not a current line-item-2 offer. The source PDF contains no text layer readable by `pdfplumber`; this pass did not compare a parsed bid-abstract JSON because none was supplied. The purchase-order OCR quality findings above apply only to that parsed artifact.


Strict parser status, source coverage, the distinct execution contexts and the preserved OOM failure are documented in [STRICT_SOURCE_PARSING.md](STRICT_SOURCE_PARSING.md). These checks do not supply missing acceptance evidence or establish perfect OCR.
