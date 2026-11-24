"""Add report font colour and clinician signatory snapshots."""
from alembic import op
import sqlalchemy as sa

revision = "0009_signatory_font_color"
down_revision = "0008_analyte_review_comments"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    user_columns = {c["name"] for c in sa.inspect(bind).get_columns("user_accounts")}
    review_columns = {c["name"] for c in sa.inspect(bind).get_columns("result_reviews")}
    clinic_columns = {c["name"] for c in sa.inspect(bind).get_columns("clinic_profile")}
    for name, typ in [
        ("full_name", sa.String(200)), ("credentials", sa.String(200)),
        ("signature_path", sa.String(500)), ("stamp_path", sa.String(500))
    ]:
        if name not in user_columns:
            op.add_column("user_accounts", sa.Column(name, typ, nullable=True))
    for name, typ in [
        ("signatory_name", sa.String(200)), ("signatory_credentials", sa.String(200)),
        ("signatory_signature_path", sa.String(500)), ("signatory_stamp_path", sa.String(500))
    ]:
        if name not in review_columns:
            op.add_column("result_reviews", sa.Column(name, typ, nullable=True))
    if "font_color" not in clinic_columns:
        op.add_column("clinic_profile", sa.Column("font_color", sa.String(7), nullable=False, server_default="#243447"))


def downgrade():
    bind = op.get_bind()
    for table, names in [
        ("clinic_profile", ["font_color"]),
        ("result_reviews", ["signatory_stamp_path", "signatory_signature_path", "signatory_credentials", "signatory_name"]),
        ("user_accounts", ["stamp_path", "signature_path", "credentials", "full_name"])
    ]:
        existing = {c["name"] for c in sa.inspect(bind).get_columns(table)}
        for name in names:
            if name in existing:
                op.drop_column(table, name)
