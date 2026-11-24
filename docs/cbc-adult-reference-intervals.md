# CBC adult reference interval catalogue — draft for local verification

**Status: research draft only. Not approved for clinical reporting or automatic flagging.**  
**Population covered:** adults aged 18 years and older. These are published comparator intervals, not Uganda-specific or HumaCount 30TS-validated intervals. The laboratory director/supervisor must select and verify the intervals appropriate to the clinic's population, analyzer, method, units and local validation before clinical use.

## Source documents

1. University of Iowa Health Care, Department of Pathology, *CBC (Complete Blood Count)*. Adult ranges are explicitly identified; the page also documents age-specific intervals.  
   https://www.healthcare.uiowa.edu/path_handbook/handbook/test299.html
2. Mayo Clinic Laboratories, *Complete Blood Cell Count (CBC) with Differential, Blood*, Test ID CBC. Published reference values include adult and age/sex-specific intervals.  
   https://www.mayocliniclabs.com/test-catalog/overview/9109

## Adult intervals for the 15 CBC Connect HumaCount fields

| Code | Analyte | Adult male | Adult female | Unit | Source |
|---|---|---:|---:|---|---|
| WBC | White blood cell count | 3.4–9.6 | 3.4–9.6 | 10^9/L | Mayo |
| RBC | Red blood cell count | 4.35–5.65 | 3.92–5.13 | 10^12/L | Mayo |
| HGB | Hemoglobin | 13.2–16.6 | 11.6–15.0 | g/dL | Mayo |
| HCT | Hematocrit | 38.3–48.6 | 35.5–44.9 | % | Mayo |
| MCV | Mean corpuscular volume | 78.2–97.9 | 78.2–97.9 | fL | Mayo |
| MCH | Mean corpuscular hemoglobin | 25–35 | 25–35 | pg | University of Iowa |
| MCHC | Mean corpuscular hemoglobin concentration | 32–36 | 32–36 | g/dL | University of Iowa |
| RDW | Red cell distribution width (CV) | 11.8–14.5 | 12.2–16.1 | % | Mayo |
| PLT | Platelet count | 135–317 | 157–371 | 10^9/L | Mayo |
| MPV | Mean platelet volume | 9.4–12.3 | 9.4–12.3 | fL | University of Iowa |
| NEU# | Absolute neutrophil count | 1.56–6.45 | 1.56–6.45 | 10^9/L | Mayo |
| LYM# | Absolute lymphocyte count | 0.95–3.07 | 0.95–3.07 | 10^9/L | Mayo |
| MONO# | Absolute monocyte count | 0.26–0.81 | 0.26–0.81 | 10^9/L | Mayo |
| EOS# | Absolute eosinophil count | 0.03–0.48 | 0.03–0.48 | 10^9/L | Mayo |
| BASO# | Absolute basophil count | 0.01–0.08 | 0.01–0.08 | 10^9/L | Mayo |

## Important implementation and safety notes

- **Do not apply these adult intervals to children or adolescents.** Mayo and Iowa publish age-stratified intervals; the application must use age-appropriate ranges once the patient's date of birth/age is reliably available.
- RBC, HGB, HCT, RDW and PLT are sex-specific in the Mayo catalogue. CBC Connect currently has no verified patient sex field. Do not guess. Show both intervals or mark interpretation as requiring the appropriate demographic context.
- A result outside a reference interval is an outlier for review, not a diagnosis. Clinical context, specimen quality, analyzer flags, delta checks and smear review may matter.
- Do not overwrite analyzer-supplied flags. Store calculated comparisons separately and retain the original result.
- Do not use a reference interval from one instrument/method as a validated HumaCount 30TS interval without local verification.
- These intervals are not critical-value thresholds and must not be used as a substitute for the laboratory's critical result policy.
- Reference interval verification must be performed by an authorized reviewer other than the person who created the draft, using documented local evidence.

## Differences between published laboratories

The University of Iowa and Mayo Clinic intervals are not identical for several CBC parameters. This is expected: reference intervals are method-, population- and laboratory-dependent. The values above use one cited source per parameter for traceability; they have not been averaged or blended.

## Suggested local approval checklist

1. Confirm HumaCount 30TS model, software version, units and reportable parameter definitions.
2. Compare the manufacturer's method-specific documentation and the laboratory's current verified intervals.
3. Review local patient population considerations, including age, sex and pregnancy where applicable.
4. Approve each analyte/population/sex interval through the application's second-person verification workflow.
5. Only after approval, enable automatic high/low comparison for that exact population and unit.
