"""add dwell_time + search_lat/lng to user_interactions + update questionnaire"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION


revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("user_interactions", sa.Column("dwell_seconds", sa.Integer()))
    op.add_column("user_interactions", sa.Column("search_lat", DOUBLE_PRECISION()))
    op.add_column("user_interactions", sa.Column("search_lng", DOUBLE_PRECISION()))
    op.create_index("idx_interactions_dwell", "user_interactions", ["dwell_seconds"])

    op.add_column("user_profiles", sa.Column("college", sa.String(200)))
    op.add_column("user_profiles", sa.Column("sleep_schedule", sa.String(50)))
    op.add_column("user_profiles", sa.Column("smoking_status", sa.String(30)))
    op.add_column("user_profiles", sa.Column("visitor_frequency", sa.String(30)))


def downgrade():
    op.drop_column("user_interactions", "dwell_seconds")
    op.drop_column("user_interactions", "search_lat")
    op.drop_column("user_interactions", "search_lng")
    op.drop_column("user_profiles", "college")
    op.drop_column("user_profiles", "sleep_schedule")
    op.drop_column("user_profiles", "smoking_status")
    op.drop_column("user_profiles", "visitor_frequency")