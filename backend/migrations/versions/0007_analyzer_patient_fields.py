"""Track which patient identity fields were supplied by the analyzer."""
from alembic import op
import sqlalchemy as sa

revision = "0007_analyzer_patient_fields"
down_revision = "0006_clinic_logo_watermark"
branch_labels = None
depends_on = None


def upgrade():
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("cbc_results")}
    if "patient_fields_from_analyzer" not in columns:
        op.add_column("cbc_results", sa.Column("patient_fields_from_analyzer", sa.JSON(), nullable=False, server_default="[]"))
    # Existing analyzer records predate field-level provenance. Treat populated
    # identity values on those records as analyzer-supplied rather than allowing
    # accidental edits. Manually registered records remain editable.
    op.execute(sa.text("""
        UPDATE cbc_results
        SET patient_fields_from_analyzer = to_json(array_remove(ARRAY[
            CASE WHEN patient_reference IS NOT NULL AND btrim(patient_reference) <> '' THEN 'patient_reference' END,
            CASE WHEN patient_name IS NOT NULL AND btrim(patient_name) <> '' THEN 'patient_name' END,
            CASE WHEN patient_age IS NOT NULL AND btrim(patient_age) <> '' THEN 'patient_age' END,
            CASE WHEN patient_address IS NOT NULL AND btrim(patient_address) <> '' THEN 'patient_address' END
        ]::text[], NULL))
        WHERE device_id <> 'manual-entry'
    """))


def downgrade():
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("cbc_results")}
    if "patient_fields_from_analyzer" in columns:
        op.drop_column("cbc_results", "patient_fields_from_analyzer")
