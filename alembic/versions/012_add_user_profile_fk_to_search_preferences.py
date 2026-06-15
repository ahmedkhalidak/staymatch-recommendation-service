"""add user_profile_id foreign key to user_search_preferences"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user_search_preferences",
        sa.Column("user_profile_id", UUID(as_uuid=True), sa.ForeignKey("user_profiles.id"), nullable=True)
    )


def downgrade():
    op.drop_column("user_search_preferences", "user_profile_id")
