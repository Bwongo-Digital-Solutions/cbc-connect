"""Store per-analyte clinician comments with each CBC review."""
from alembic import op
import sqlalchemy as sa

revision = "0008_analyte_review_comments"
down_revision = "0007_analyzer_patient_fields"
branch_labels = None
depends_on = None


def upgrade():
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("result_reviews")}
    if "analyte_comments" not in columns:
        op.add_column("result_reviews", sa.Column("analyte_comments", sa.JSON(), nullable=False, server_default="{}"))


def downgrade():
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("result_reviews")}
    if "analyte_comments" in columns:
        op.drop_column("result_reviews", "analyte_comments")
