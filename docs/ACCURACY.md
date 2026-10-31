# LIVE extraction accuracy

- Date: 2026-10-31 (documents read 2026-10-30 to 2026-10-31)
- Model: gemini-3.5-flash (served as gemini-3.6-flash)
- Folder: problem (synthetic documents with ground truth)
- Documents read: 37 of 37; pages sent: 37; schema mismatches: 0
- PDFs were rendered to PNG at 144 dpi, so the model read pixels, not the PDF text layer.
- Review threshold: confidence below 0.85, a null value, or a schema mismatch.

Produced by `python tools/measure_extraction.py --folder problem --mode live`. Numbers come only from running the script.

**Field accuracy: 304 / 305 = 99.7%**

- Misread or missing fields: 1; sent to review: 0; not sent to review (auto-approved): 1
- Correct fields sent to review anyway: 0
- Null answers for fields the document does not carry (not scored, not shown in the app): 2

## Per document type

| kind | correct | total | accuracy | sent to review |
|---|---:|---:|---:|---:|
| delivery_note | 4 | 4 | 100.0% | 0 |
| export_invoice | 48 | 48 | 100.0% | 0 |
| gas_invoice | 72 | 72 | 100.0% | 0 |
| mill_certificate | 84 | 84 | 100.0% | 0 |
| production_register | 49 | 49 | 100.0% | 0 |
| purchase_invoice | 33 | 33 | 100.0% | 0 |
| scrap_register | 3 | 3 | 100.0% | 0 |
| stock_register | 7 | 7 | 100.0% | 0 |
| verification_report | 4 | 5 | 80.0% | 0 |

## Per field

| field | correct | total | accuracy | sent to review |
|---|---:|---:|---:|---:|
| cert_no | 7 | 7 | 100.0% | 0 |
| chemistry.C | 7 | 7 | 100.0% | 0 |
| chemistry.Cr | 7 | 7 | 100.0% | 0 |
| chemistry.Mn | 7 | 7 | 100.0% | 0 |
| chemistry.Ni | 7 | 7 | 100.0% | 0 |
| chemistry.Si | 7 | 7 | 100.0% | 0 |
| chemistry.other | 7 | 7 | 100.0% | 0 |
| cn_code | 8 | 8 | 100.0% | 0 |
| date | 13 | 13 | 100.0% | 0 |
| destination | 8 | 8 | 100.0% | 0 |
| emission_factor_t_per_tj | 12 | 12 | 100.0% | 0 |
| emissions_claim | 3 | 3 | 100.0% | 0 |
| factory | 1 | 1 | 100.0% | 0 |
| fuel | 12 | 12 | 100.0% | 0 |
| grade | 7 | 7 | 100.0% | 0 |
| heat | 12 | 12 | 100.0% | 0 |
| heats | 1 | 1 | 100.0% | 0 |
| invoice_no | 25 | 25 | 100.0% | 0 |
| label | 0 | 1 | 0.0% | 0 |
| mill | 9 | 9 | 100.0% | 0 |
| month | 12 | 12 | 100.0% | 0 |
| note_no | 1 | 1 | 100.0% | 0 |
| period_year | 1 | 1 | 100.0% | 0 |
| precursor_see | 1 | 1 | 100.0% | 0 |
| production.cn_code | 12 | 12 | 100.0% | 0 |
| production.heats | 12 | 12 | 100.0% | 0 |
| production.month | 12 | 12 | 100.0% | 0 |
| production.tonnes | 12 | 12 | 100.0% | 0 |
| production_date | 7 | 7 | 100.0% | 0 |
| production_months | 8 | 8 | 100.0% | 0 |
| quantity | 12 | 12 | 100.0% | 0 |
| report_no | 1 | 1 | 100.0% | 0 |
| scrap.pre_consumer_share | 1 | 1 | 100.0% | 0 |
| scrap.sources | 1 | 1 | 100.0% | 0 |
| scrap.tonnes | 1 | 1 | 100.0% | 0 |
| stock.closing.heat | 1 | 1 | 100.0% | 0 |
| stock.closing.mill | 1 | 1 | 100.0% | 0 |
| stock.closing.tonnes | 1 | 1 | 100.0% | 0 |
| stock.count_note | 1 | 1 | 100.0% | 0 |
| stock.opening.heat | 1 | 1 | 100.0% | 0 |
| stock.opening.mill | 1 | 1 | 100.0% | 0 |
| stock.opening.tonnes | 1 | 1 | 100.0% | 0 |
| supplier | 6 | 6 | 100.0% | 0 |
| supplier_type | 5 | 5 | 100.0% | 0 |
| tonnes | 20 | 20 | 100.0% | 0 |
| unit | 12 | 12 | 100.0% | 0 |

## Misread or missing fields

| document | field | ground truth | LIVE value | sent to review |
|---|---|---|---|---|
| VR-A.pdf | label | Commission example value used as a synthetic stand-in. Not a real mill, not a default value. | Note: Commission example value used as a synthetic stand-in. Not a real mill, not a default value. | NO |

## Checks on LIVE fields

Every document's LIVE fields, with the demo review rule: fields sent to review count as missing until a person approves them.

- Flags raised: CERT_NO_PURCHASE, CHEMISTRY_RANGE, FUEL_UNIT, MASS_BALANCE, PRECURSOR_EVIDENCE
- Planted flags expected: CERT_NO_PURCHASE, CHEMISTRY_RANGE, FUEL_UNIT, MASS_BALANCE, PRECURSOR_EVIDENCE
- Planted flags missed: none
- Extra flags (raised by misreads or by fields awaiting review): none
- CHEMISTRY_RANGE (swapped Mn/Cr certificate) caught from LIVE fields: yes
- Precursor statuses equal to expected: 6 of 6

