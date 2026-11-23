"""Add patient demographics and clinic-wide document branding."""
from alembic import op
import sqlalchemy as sa

revision = "0005_clinic_branding_patient"
down_revision = "0004_document_annotations"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    result_columns = {c["name"] for c in sa.inspect(bind).get_columns("cbc_results")}
    for name, column in (
        ("patient_name", sa.Column("patient_name", sa.String(length=200), nullable=True)),
        ("patient_age", sa.Column("patient_age", sa.String(length=80), nullable=True)),
        ("patient_address", sa.Column("patient_address", sa.Text(), nullable=True)),
    ):
        if name not in result_columns:
            op.add_column("cbc_results", column)

    tables = set(sa.inspect(bind).get_table_names())
    if "clinic_profile" not in tables:
        op.create_table(
            "clinic_profile",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("clinic_name", sa.String(length=200), nullable=False, server_default="Clinic"),
            sa.Column("address", sa.Text(), nullable=False, server_default=""),
            sa.Column("phone", sa.String(length=120), nullable=False, server_default="0775-872-454, 0751-319-201"),
            sa.Column("email", sa.String(length=160), nullable=False, server_default=""),
            sa.Column("theme_color", sa.String(length=7), nullable=False, server_default="#0879D9"),
            sa.Column("header_text", sa.Text(), nullable=False, server_default=""),
            sa.Column("footer_text", sa.Text(), nullable=False, server_default="Powered by ClinicHIS"),
            sa.Column("logo_path", sa.String(length=500), nullable=True),
            sa.Column("updated_by", sa.String(length=120), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade():
    bind = op.get_bind()
    if "clinic_profile" in sa.inspect(bind).get_table_names():
        op.drop_table("clinic_profile")
    columns = {c["name"] for c in sa.inspect(bind).get_columns("cbc_results")}
    for name in ("patient_address", "patient_age", "patient_name"):
        if name in columns:
            op.drop_column("cbc_results", name)
