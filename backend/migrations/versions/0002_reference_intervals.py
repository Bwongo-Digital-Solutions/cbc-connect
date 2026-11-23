"""Sourced reference interval governance records."""
from alembic import op
from app.models import ReferenceInterval
revision = "0002_reference_intervals"
down_revision = "0001_initial"
branch_labels = None
depends_on = None
def upgrade():
    ReferenceInterval.__table__.create(bind=op.get_bind(), checkfirst=True)
def downgrade():
    ReferenceInterval.__table__.drop(bind=op.get_bind(), checkfirst=True)
