"""Store separate annotated document versions; tolerate metadata-created tables."""
from alembic import op
import sqlalchemy as sa

revision = "0004_document_annotations"
down_revision = "0003_result_documents"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("result_documents")}
    if "parent_document_id" not in columns:
        op.add_column("result_documents", sa.Column("parent_document_id", sa.Integer(), nullable=True))
    if "document_kind" not in columns:
        op.add_column("result_documents", sa.Column("document_kind", sa.String(length=20), nullable=False, server_default="SOURCE"))
    if "annotation_data" not in columns:
        op.add_column("result_documents", sa.Column("annotation_data", sa.JSON(), nullable=True))
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("result_documents")}
    if "ix_result_documents_parent_document_id" not in indexes:
        op.create_index("ix_result_documents_parent_document_id", "result_documents", ["parent_document_id"])

def downgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("result_documents")}
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("result_documents")}
    if "ix_result_documents_parent_document_id" in indexes:
        op.drop_index("ix_result_documents_parent_document_id", table_name="result_documents")
    for name in ("annotation_data", "document_kind", "parent_document_id"):
        if name in columns:
            op.drop_column("result_documents", name)
