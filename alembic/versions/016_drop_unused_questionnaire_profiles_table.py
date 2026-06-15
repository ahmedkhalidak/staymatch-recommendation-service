"""drop unused questionnaire_profiles cache table"""
from alembic import op
import sqlalchemy as sa


revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade():
    # Drop the unused questionnaire_profiles table
    op.drop_table("questionnaire_profiles")


def downgrade():
    # Recreate questionnaire_profiles table if needed
    op.create_table(
        "questionnaire_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_profile_id", sa.UUID(), nullable=False),
        sa.Column("completion_percentage", sa.Integer(), server_default=sa.text("0")),
        sa.Column("last_answered_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_profile_id"], ["user_profiles.id"]),
        sa.UniqueConstraint("user_profile_id")
    )
    op.create_index("idx_questionnaire_profiles_user", "questionnaire_profiles", ["user_profile_id"])
