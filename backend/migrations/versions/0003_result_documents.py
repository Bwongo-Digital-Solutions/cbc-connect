"""Add uploaded source documents for CBC results."""
from alembic import op
from app.models import ResultDocument

revision = "0003_result_documents"
down_revision = "0002_reference_intervals"
branch_labels = None
depends_on = None

def upgrade():
    # The initial migration creates the full current metadata in this project.
    # Keep this revision safe for both fresh and already-initialized databases.
    ResultDocument.__table__.create(bind=op.get_bind(), checkfirst=True)

def downgrade():
    ResultDocument.__table__.drop(bind=op.get_bind(), checkfirst=True)
