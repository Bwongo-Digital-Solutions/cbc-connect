# DOCX report template guide

Upload DOCX files from the Report templates screen. PDF uploads are retained as reference documents and cannot be merged.

The renderer uses docxtpl/Jinja placeholders. Add placeholders as normal Word text runs:
- {{ sample_id }}
- {{ patient_reference }}
- {{ patient_name }}
- {{ patient_age }}
- {{ patient_address }}
- {{ clinic_name }}
- {{ clinic_address }}
- {{ clinic_phone }}
- {{ clinic_email }}
- {{ header_text }}
- {{ footer_text }}
- {{ analyzer }}
- {{ reviewer }}
- {{ comments }}
- {{ received_at }}
- {{ reviewed_at }}

For a table of measurements, add a row with a Jinja loop:
- {% for item in results %}
- {{ item.code }} | {{ item.value }} | {{ item.unit }} | {{ item.flag }}
- {% endfor %}

Keep the loop tags in separate table cells/paragraphs where required by docxtpl. Avoid splitting a single placeholder across multiple Word formatting runs. Test each template with synthetic records, check page breaks and verify units/precision before approving local use.

Generated reports are based only on REVIEWED results and the saved review values. The application does not determine clinical validity or release authority.

## Generate a starter template from the clinic workspace

If the clinic has no DOCX report template, open **Report templates** and select **Generate sample template**. CBC Connect creates an editable DOCX starter with clinic name, sample and patient reference, analyzer, review metadata, a results table and comments placeholders. It is added to the template list and can then be customized in Word or LibreOffice and uploaded as the clinic's approved template.

The action is idempotent: if a DOCX template already exists, the API returns the existing template rather than creating another starter. PDF files alone do not count as a mergeable DOCX template. The starter is a layout aid, not an approved clinical report; the clinic must add its identity, verify fields and formatting, and approve it under local procedures before use.


Every generated DOCX-template report is also given the saved clinic logo, clinic name, theme colour, address/header and footer automatically. CBC Connect adds a patient identity table containing patient name, age and address even when those fields are not explicitly placed in the uploaded template. The footer always includes **Powered by ClinicHIS** and both configured standard contact numbers (0775-872-454 and 0751-319-201). The same saved clinic profile is used by the branded PDF generator and the direct **Print branded final PDF** action.
