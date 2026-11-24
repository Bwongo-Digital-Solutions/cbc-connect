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
    # accidental edits. Manually registered records remain editable. Use
    # SQLAlchemy JSON binding so this works with both SQLite CI and PostgreSQL.
    table = sa.table(
        "cbc_results",
        sa.column("id", sa.Integer),
        sa.column("device_id", sa.String),
        sa.column("patient_reference", sa.String),
        sa.column("patient_name", sa.String),
        sa.column("patient_age", sa.String),
        sa.column("patient_address", sa.Text),
        sa.column("patient_fields_from_analyzer", sa.JSON),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(
            table.c.id, table.c.patient_reference, table.c.patient_name,
            table.c.patient_age, table.c.patient_address
        ).where(table.c.device_id != "manual-entry")
    ).mappings()
    for row in rows:
        fields = [
            field for field in ("patient_reference", "patient_name", "patient_age", "patient_address")
            if row[field] is not None and str(row[field]).strip()
        ]
        connection.execute(
            table.update().where(table.c.id == row["id"]).values(patient_fields_from_analyzer=fields)
        )


def downgrade():
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("cbc_results")}
    if "patient_fields_from_analyzer" in columns:
        op.drop_column("cbc_results", "patient_fields_from_analyzer")
