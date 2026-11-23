# DOCX report template guide

Upload DOCX files from the Report templates screen. PDF uploads are retained as reference documents and cannot be merged.

The renderer uses docxtpl/Jinja placeholders. Add placeholders as normal Word text runs:
- {{ sample_id }}
- {{ patient_reference }}
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
