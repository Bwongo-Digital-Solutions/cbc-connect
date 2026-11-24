# CBC Connect — Simple User Guide for Laboratory Staff and Clinicians

**Who this guide is for:** laboratory technicians, clinicians, laboratory supervisors and clinic administrators.  
**Purpose:** show staff how to find a CBC result, open its source report, add notes and record a review.

> **Important:** CBC Connect is still a development system. Do not use its demo records for patient care. A status of **REVIEWED** means that a review was saved in the software; it does not mean that a result has been formally authorized or released to a patient.

## 1. Sign in

1. Open the CBC Connect web address given to you by your system administrator.
2. Enter your own username and password.
3. Select **Sign in**.
4. When you finish, select **Sign out**.

Do not share your password or use another staff member's account.

## 2. Find a CBC result

After signing in, you will see the **Results queue**.

- **Total results** shows all results and registered samples.
- **Pending review** shows results that still need staff review.
- **Reviewed** shows results for which a review has been saved.

Use the search box to find a sample by its laboratory number, patient reference or analyzer. Use the status list to show only pending or reviewed results. Select **Refresh** to check for new results.

Select **Open** beside a result to see its details.

## 3. Check that you have the correct sample

Before reviewing anything:

1. Compare the sample/accession number with the laboratory request and the specimen label.
2. Check the patient reference, if one is recorded.
3. Check the analyzer name and the time the result arrived.
4. If anything does not match, stop and ask the laboratory supervisor to help. Do not guess or change the patient or sample identity.

## 4. Open an uploaded CBC report

The result detail screen has a section called **Uploaded CBC report / source document**.

To add a report:
1. Select **Choose source report**.
2. Select the PDF, DOC, DOCX, PNG or JPG file supplied by the laboratory/analyzer workflow.
3. Add a short note if needed.
4. Select **Upload source document**.

To view a report:
1. Find the uploaded file in the document list.
2. Select **View document**.
3. The report opens in the document viewer. Use the viewer controls to zoom or move between PDF pages.
4. Close the viewer to return to the CBC result.

The uploaded file is kept as the original source document. CBC Connect does not silently change or replace it. Any annotations are saved as a separate copy.

### Annotate an uploaded report

1. Select **Annotate** beside an original PDF, DOC, DOCX, PNG or JPG source document. Word files are converted to a PDF preview for annotation; the uploaded Word original is retained.
2. Choose **Highlight**, **Pen**, **Text** or **Comment** from the toolbar. For a PDF, use the page controls to move through its pages.
3. Use the pointer on the report to place the annotation. Text and comment tools ask you to enter the wording.
4. Select **Save annotated copy**. CBC Connect stores a new annotated PDF or image and records who saved it and when.
5. The annotated copy appears as a separate document. The original source upload remains unchanged and can still be opened.

For PDF and Word files, the annotated copy is exported as PDF. For images, the annotated copy is saved as PNG. Use **Export PDF** to download a printable PDF, or **Print** to send the document to the workstation printer. DOC and DOCX files are converted to PDF for preview, annotation and printing; downloading the original Word upload remains separate. The editor adds visual annotations; it does not rewrite existing document text, change printed CBC values, or alter analyzer measurements. Check annotations carefully before using or sharing the copy. An annotation is not a clinical correction or authorization.

### Add or change your notes

Each uploaded document has a **Clinician / reviewer notes** box.

1. Type your note in the box.
2. Select **Save notes**.
3. The note is saved against that document and the action is recorded in the result history.

Use notes to explain a document discrepancy or record the review context. Do not use notes to replace the original report or to change the patient's identity.

## 5. Review the CBC measurements

The **Analyzer measurements** table shows the values originally received by CBC Connect.

1. Open the source report and compare it with the measurements shown on screen.
2. Follow your laboratory's approved procedures and quality-control checks.
3. If a value or sample detail looks wrong, stop and ask the supervisor. Do not make an unsupported correction.
4. If you are authorized to record the review, use the **Review and document values** section.
5. Enter any permitted correction in the review form and explain it in **Review comments**.
6. Select **Record review** only after the required checks are complete.

The original analyzer measurements remain unchanged. The software stores reviewed values separately so staff can see what was received and what was recorded during review.

A result marked **REVIEWED** is not automatically approved for patient release. Continue to follow the clinic's own authorization and communication process.

## 6. Patient details and branded final report

Before generating a final report:
1. Open the CBC result and confirm the correct patient and sample identity.
2. Patient name, age, address, gender, patient contact, patient reference, requesting officer, requested test and collection date/time can be supplied by the analyzer or completed from the approved laboratory request when missing. The sample/accession ID comes from the incoming result.
3. Fields received from the analyzer are marked **Received from analyzer · read-only** and cannot be changed in the result viewer. This protects the original identity data.
4. If the incoming data does not contain a patient or request field, that field remains editable so authorized staff can complete it from the approved source record. Date received is recorded automatically by the system; the collection date and time are captured together. Details entered during manual sample registration also remain editable unless the analyzer later supplies that field.
5. Verify all identity details against the source CBC report and laboratory request. If analyzer-supplied information appears wrong, stop and ask the supervisor to resolve it through the approved correction process; do not overwrite the received value in the viewer.
6. Select **Save missing details** to save only editable fields. The application keeps analyzer-supplied identity values unchanged.
7. A final report can only be generated after a result has a saved review. Select **Generate branded final PDF** to download the report, or **Print branded final PDF** to open it in the browser print dialog. The generated PDF uses the clinic's saved logo, theme colour, header, address and footer.
8. Check the patient identity, sample details, measurements, units and comments before printing or sharing.

The branded report footer includes **Powered by ClinicHIS** and the clinic contact numbers. The original uploaded source document and original analyzer measurements are not changed.

## 7. Configure clinic document branding

Clinic supervisors and administrators can open the **Clinic branding** tab to set the default layout used for every newly generated final CBC PDF.

- Clinic name, address, email and contact numbers.
- Theme colour using a six-digit hex colour (for example, `#0879D9`).
- Clinic logo (PNG or JPG, maximum 2 MB).
- Optional additional header text.
- Footer text. The generated footer also includes Powered by ClinicHIS and the configured contact numbers.

Select **Save clinic branding**. The settings are stored in the clinic database and reused automatically; they do not need to be entered for every report. Return to this tab to edit the defaults. Changes apply to reports generated after the change; previously generated PDFs remain as they were.

Patient name, age, address, gender, patient contact, patient reference, requesting officer, requested test and collection date/time are taken from incoming analyzer data when supplied. Analyzer-supplied fields are read-only in the result viewer; only missing fields can be completed there. Sample/accession ID received from the analyzer is also read-only. Manually registered patient details remain editable unless a later analyzer message supplies that field. Verify every value against the source records. Do not copy patient details from another record.

Only use a report for its intended purpose after the responsible staff have completed the clinic's approval process. A PDF uploaded as a source document is for viewing; it is not a report template.

## 8. User roles

| Role | What the role can do |
| --- | --- |
| TECHNICIAN | Register samples, view results, attach source documents, add document notes and record a result review. |
| CLINICIAN | View results, open and attach source documents, add notes and record a result review. |
| SUPERVISOR | Technician functions, plus manage analyte display settings and report templates. |
| ADMIN | Supervisor functions, plus create staff accounts. |

Your administrator assigns your role. If a button or section is not available, ask the administrator to check your access. Do not share accounts to get around a permission.

## 9. Supervisor: report templates and analyte display

Supervisors and administrators can manage the clinic's report templates and analyte display settings.

If the clinic does not have a DOCX report template:
1. Open **Report templates**.
2. Select **Generate sample template**.
3. Download the DOCX file.
4. Customize it using the clinic's approved wording and layout.
5. Test it with synthetic demo records.
6. Obtain the required local approval, then upload the clinic's approved template.

Analyte display settings change labels and display formatting only. They do not validate results, change units, or define clinical reference intervals.

## 10. Demo results

The system includes fictional CBC records for training and software demonstration. The first demo record can also generate a sample PDF source report from its fictional values. Open the record named **SYNTH-CBC-0001**, select **Create demo report PDF**, then select **View document**.

The demo report is clearly marked **SYNTHETIC TRAINING DATA ONLY — NOT A PATIENT REPORT**. It is not a real analyzer export, not a real patient result, and not suitable for clinical decisions. Do not upload demo documents into a real patient record or use demo values for patient care.

## 11. If something goes wrong

| Problem | What to do |
| --- | --- |
| You cannot sign in | Check that you are using your own account. Ask the administrator to check that it is active. |
| You cannot find a result | Select **Refresh**, clear the search box and set the status filter to **All statuses**. |
| The sample or patient details do not match | Stop. Ask the laboratory supervisor to resolve the mismatch. |
| A PDF or image will not upload | Check that it is a PDF, DOC, DOCX, PNG or JPG and smaller than 15 MB. |
| A document will not open | Refresh the result and try again. If it still fails, ask the administrator to check the stored file. |
| You cannot save notes or a review | Check your account role and ask the administrator if access is correct. |
| Analyzer results are not arriving | Contact the system administrator. The native HumaCount connection is not yet validated in this development build. |

## 12. Protect patient information

- Use only the patient information needed for your approved work.
- Do not use real patient details in demo records, screenshots or public support messages.
- Do not share passwords, access tokens or API keys.
- Use CBC Connect only on a network and workstation approved by your organization.
- Follow your facility's privacy, retention and access policies.

## Quick reminder

**Find the result → check the sample identity → open the source report → compare the measurements → add notes if needed → record a review only when authorized → follow the clinic's separate result-approval process.**

CBC Connect records work in the application. It does not replace your laboratory's approved procedures or professional responsibilities.
