"""Add configurable document font family to clinic branding."""
from alembic import op
import sqlalchemy as sa

revision = "0010_document_font_family"
down_revision = "0009_signatory_font_color"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("clinic_profile")}
    if "font_family" not in columns:
        op.add_column("clinic_profile", sa.Column("font_family", sa.String(80), nullable=False, server_default="Arial"))


def downgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("clinic_profile")}
    if "font_family" in columns:
        op.drop_column("clinic_profile", "font_family")
