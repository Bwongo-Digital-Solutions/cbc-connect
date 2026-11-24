"""Add patient and specimen request metadata to CBC results."""
from alembic import op
import sqlalchemy as sa

revision = "0011_cbc_request_metadata"
down_revision = "0010_document_font_family"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("cbc_results")}
    additions = [
        sa.Column("gender", sa.String(30), nullable=True),
        sa.Column("patient_contact", sa.String(80), nullable=True),
        sa.Column("requesting_officer", sa.String(200), nullable=True),
        sa.Column("requested_test", sa.Text(), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
    ]
    for column in additions:
        if column.name not in columns:
            op.add_column("cbc_results", column)


def downgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("cbc_results")}
    for name in ("collected_at", "requested_test", "requesting_officer", "patient_contact", "gender"):
        if name in columns:
            op.drop_column("cbc_results", name)
