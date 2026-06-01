"""create matching tables (roommate_matches)"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "roommate_matches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("seeker_user_id", sa.String(255), nullable=False),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("synced_rooms.id"), nullable=False),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("synced_properties.id"), nullable=False),
        sa.Column("room_compatibility_score", sa.Float(), nullable=False),
        sa.Column("match_breakdown", JSONB()),
        sa.Column("current_roommates", JSONB()),
        sa.Column("seeker_questionnaire_match", sa.Float()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column("expires_at", sa.DateTime()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("seeker_user_id", "room_id"),
    )
    op.create_index("idx_match_seeker", "roommate_matches", ["seeker_user_id"])
    op.create_index("idx_match_room", "roommate_matches", ["room_id"])
    op.create_index("idx_match_score", "roommate_matches", [sa.text("room_compatibility_score DESC")])
    op.create_index("idx_match_expires", "roommate_matches", ["expires_at"])


def downgrade():
    op.drop_table("roommate_matches")