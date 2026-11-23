"""Store separate annotated document versions."""
from alembic import op
import sqlalchemy as sa

revision = "0004_document_annotations"
down_revision = "0003_result_documents"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("result_documents", sa.Column("parent_document_id", sa.Integer(), nullable=True))
    op.add_column("result_documents", sa.Column("document_kind", sa.String(length=20), nullable=False, server_default="SOURCE"))
    op.add_column("result_documents", sa.Column("annotation_data", sa.JSON(), nullable=True))
    op.create_index("ix_result_documents_parent_document_id", "result_documents", ["parent_document_id"])

def downgrade():
    op.drop_index("ix_result_documents_parent_document_id", table_name="result_documents")
    op.drop_column("result_documents", "annotation_data")
    op.drop_column("result_documents", "document_kind")
    op.drop_column("result_documents", "parent_document_id")
