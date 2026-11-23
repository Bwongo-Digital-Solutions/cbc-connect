"""Add clinic logo watermark preferences."""
from alembic import op
import sqlalchemy as sa

revision = "0006_clinic_logo_watermark"
down_revision = "0005_clinic_branding_patient"
branch_labels = None
depends_on = None


def upgrade():
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("clinic_profile")}
    if "logo_display_mode" not in columns:
        op.add_column("clinic_profile", sa.Column("logo_display_mode", sa.String(length=20), nullable=False, server_default="header"))
    if "logo_opacity" not in columns:
        op.add_column("clinic_profile", sa.Column("logo_opacity", sa.Float(), nullable=False, server_default="0.10"))


def downgrade():
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("clinic_profile")}
    if "logo_opacity" in columns:
        op.drop_column("clinic_profile", "logo_opacity")
    if "logo_display_mode" in columns:
        op.drop_column("clinic_profile", "logo_display_mode")
