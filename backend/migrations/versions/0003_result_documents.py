"""Add uploaded source documents for CBC results."""
from alembic import op
import sqlalchemy as sa

revision = "0003_result_documents"
down_revision = "0002_reference_intervals"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "result_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("result_id", sa.Integer(), sa.ForeignKey("cbc_results.id"), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("uploaded_by", sa.String(length=120), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_result_documents_result_id", "result_documents", ["result_id"])

def downgrade():
    op.drop_index("ix_result_documents_result_id", table_name="result_documents")
    op.drop_table("result_documents")
