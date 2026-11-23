# CBC Connect — Laboratory Technician and Clinician User Manual

**Audience:** laboratory technicians, laboratory supervisors, clinicians who are authorized to view CBC results, and clinic administrators.  
**Product status:** development build. This manual describes the current standalone CBC Connect interface; it is not an analyzer installation guide or a clinical procedure.

## 1. What CBC Connect does

CBC Connect is a standalone workspace for registering samples, receiving normalized CBC analyzer data, reviewing measurements, keeping an audit history, and preparing a report from reviewed results.

The current build is designed around a human review step:

- Newly registered or received results enter **PENDING REVIEW**.
- The original received analyzer measurements are retained.
- A reviewer can record a separate set of reviewed values and comments.
- Submitting a review changes the application status to **REVIEWED**.
- A reviewed status is an application workflow state. It does **not**, by itself, mean that a result has been clinically authorized, released to a patient, or transmitted to an EMR.

The current HumaCount 30TS integration is not yet a validated device connection. The application accepts a normalized development payload; it does not currently parse a confirmed native HumaCount export or communicate with the analyzer directly.

## 2. User roles and access

The current application defines these account roles:

| Role | Current access |
| --- | --- |
| TECHNICIAN | View the workspace, register samples, open results, and submit result reviews. |
| SUPERVISOR | Technician access, plus manage analyte display configuration and report templates. |
| ADMIN | Supervisor access, plus create user accounts. |

There is currently no separate **CLINICIAN** role or clinician-specific approval/sign-off workflow. A clinician who needs access must be assigned an existing role by the clinic administrator according to local policy. Do not give a user elevated access simply to work around a missing permission.

All users should use their own account. Review identity is taken from the signed-in account, not from a name typed into the review form.

## 3. Sign in

1. Open the CBC Connect address supplied by your administrator (the development default is `http://localhost:5174` on the host running the application).
2. Enter your assigned username and password.
3. Select **Sign in**.
4. When finished, select **Sign out**. Do not share accounts or leave a workstation signed in unattended.

If sign-in fails, check the username and password with the administrator. Accounts must be active and the API must be available. Do not repeatedly guess passwords or share credentials in support messages.

## 4. Understand the dashboard and results queue

After signing in, the **Results queue** is the main workspace.

The summary cards show:
- **Total results:** all registered and received records.
- **Pending review:** records waiting for a review to be recorded.
- **Reviewed:** records with a saved review.

Use the search box to search by sample ID, patient reference, or analyzer name. Use the status filter to show all results, pending review, or reviewed results. Select **Refresh** to reload the queue.

Open a record to view its details. Check the sample ID and patient reference carefully before working on a result. If the identifiers do not match the laboratory request or specimen, stop and follow the clinic's discrepancy procedure; do not guess which patient the sample belongs to.

## 5. Register a sample manually

Use **Register sample** when a sample needs a record before analyzer data arrives.

1. Open the **Register sample** tab.
2. Enter the laboratory accession number or barcode in **Sample / accession ID**.
3. Enter the patient reference if available and permitted by clinic policy.
4. Select **Register sample**.
5. Confirm that the application reports successful registration and that the record appears in the results queue as **PENDING REVIEW**.

Use the same accession/barcode that will accompany the analyzer result. The application rejects a duplicate manual sample ID. If a sample is already registered, open the existing record rather than creating another identifier.

A manually registered sample initially has no analyzer measurements. When matching analyzer data is ingested for that sample, the incoming measurements can be attached to that registered record.

## 6. Review a received CBC result

Only review results when you are authorized and have followed the laboratory's approved SOP, including specimen identity checks and any required analyzer/QC checks.

1. In **Results queue**, find the correct sample and select **Open**.
2. Verify the sample ID and patient reference against the laboratory request and specimen identifiers.
3. Check the analyzer and device information and the received timestamp.
4. Read the **Analyzer measurements** table. These are the original values received by CBC Connect.
5. Compare the values with the analyzer output and the applicable laboratory procedure. Investigate missing, unexpected, inconsistent, or questionable data before proceeding.
6. In **Review and document values**, check each analyte and its value, unit, and flag. Record only changes that are supported by the source record and authorized procedure. Add a clear comment explaining any correction or relevant issue.
7. Select the review/submit button and confirm that the record now shows **REVIEWED**.

The reviewed analyte set must contain the same analyte codes as the received set. If a result is incomplete or cannot be reconciled, do not submit a review merely to clear the queue. Escalate it to the supervisor and use the local exception procedure.

### Important: original versus reviewed values

The original analyzer values are retained separately and are not overwritten by a review. The review stores the values submitted by the reviewer and the reviewer comments. Always distinguish the original analyzer output from any reviewed or corrected value when investigating a discrepancy.

The current application does not provide a second-person clinical authorization step, automatic delta checks, validated reference-interval flagging, or a clinician release workflow. Follow the laboratory's existing authorization and result-release process outside this development build.

## 7. View audit history

Open a result to inspect its recorded review information and audit events (where displayed). The audit history is intended to help staff understand events such as sample registration, analyzer result receipt, attachment to a manually registered sample, and review submission.

If an action or value appears incorrect, do not try to conceal or erase it. Notify the supervisor and follow the clinic's correction and incident-reporting process.

## 8. Print or generate a report

A report can be generated only for a result whose status is **REVIEWED**.

### Print a reviewed result

1. Open the reviewed result.
2. Select **Print report / PDF**.
3. Use the browser print dialog to print or save the page as PDF, if permitted by clinic policy.
4. Verify patient/sample identifiers, values, units, reviewer and comments before using the document.

### Generate a PDF from a DOCX template

1. A supervisor or administrator should prepare and upload the clinic-approved DOCX template under **Report templates**.
2. Open a reviewed result.
3. Choose the DOCX template in the report-template selector.
4. Select **Generate PDF from template**.
5. Open the generated PDF and verify its contents and layout before any authorized use.

PDF uploads in the template area are retained as reference documents; they are not mergeable report templates. Only DOCX templates can be used for template-based PDF generation.

## 9. Supervisor tasks

The **Analyte setup** and **Report templates** tabs are restricted to supervisors and administrators.

### Analyte setup

An authorized supervisor can configure an analyte code, display name, unit, decimal precision, and enabled state. These settings affect local display configuration; they do not convert or validate incoming measurements and do not establish clinical reference intervals.

Do not invent analyte codes, units, precision, or reference limits. Confirm local conventions with the laboratory lead and the analyzer documentation.

### Report templates

If the clinic has no DOCX template:

1. Open **Report templates**.
2. Select **Generate sample template**.
3. Download the generated DOCX.
4. Customize it in an approved word processor with the clinic identity and required report fields.
5. Test it using synthetic/demo records.
6. Have the responsible laboratory authority approve it under local procedures.
7. Upload the approved DOCX and select it when generating reports.

The starter document is only a layout aid; it is not a clinically approved report. See [Report template guide](report-template-guide.md) for supported placeholders and table formatting.

## 10. Synthetic demonstration records

Development installations can be populated with fictional records using the repository's demo seeding script. These records are explicitly labelled as simulated training data and should be used only in an isolated demonstration or test environment.

Never confuse a sample beginning with `SYNTH-CBC-` or a patient reference beginning with `SYNTH-PATIENT-` with a real patient. Do not copy demo values into a patient record or use them for training clinical decisions. See [Synthetic demo data](synthetic-demo-data.md).

## 11. Common problems

| Problem | What to do |
| --- | --- |
| Cannot sign in | Confirm the account is active, check credentials, and ask the administrator to check API availability. |
| Results queue is empty | Select **Refresh**; check the search and status filters; confirm that a sample was registered or that the analyzer integration/ingestion service is operating. |
| Duplicate sample warning | Search for and open the existing sample. Do not invent a new accession number to bypass the warning. |
| Result is still pending | A result remains pending until an authorized reviewer submits a review. Do not submit a review without completing the required checks. |
| Cannot open Analyte setup or Report templates | These functions require SUPERVISOR or ADMIN access. Ask the administrator to confirm your role. |
| Cannot generate a template PDF | Confirm the result is REVIEWED, a DOCX template is uploaded and selected, and the template file is available. A PDF reference upload cannot be merged. |
| Analyzer result does not appear | The current build does not yet include a validated native HumaCount parser/receiver. Confirm the device integration status with the technical administrator. |
| Values or identifiers appear wrong | Stop the workflow, preserve the original analyzer output, and escalate to the supervisor. Do not guess or silently change patient/sample identifiers. |

## 12. Patient privacy and safe use

- Use only the minimum patient information required by the clinic's approved workflow.
- Do not use real patient identifiers in screenshots, demo fixtures, issue reports, or public support requests.
- Do not share passwords, API keys, access tokens, or database backups.
- Use the application only on an approved, access-controlled network and follow clinic retention, consent, confidentiality, and access policies.
- Do not use this development build as the sole system for diagnosis, treatment decisions, result authorization, or patient result release.
- Before any live clinical use, the deploying organization must complete security assessment, operational acceptance, device/interface validation, clinical workflow validation, staff training, backup/restore testing, and formal approval.

## 13. Quick workflow summary

**Register sample → confirm identity → receive analyzer data → compare original measurements with source/QC and SOP → document review → supervisor/authorized clinical release under local policy → generate/verify report.**

CBC Connect's **REVIEWED** status records an application review only. Follow your facility's approved process for final authorization and communication of results.
