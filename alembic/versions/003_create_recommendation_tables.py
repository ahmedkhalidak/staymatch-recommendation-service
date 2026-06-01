"""create recommendation tables (property/room recommendations)"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "property_recommendations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("synced_properties.id"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("score_breakdown", JSONB()),
        sa.Column("rank", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column("expires_at", sa.DateTime()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "property_id"),
    )
    op.create_index("idx_prop_rec_user", "property_recommendations", ["user_id"])
    op.create_index("idx_prop_rec_score", "property_recommendations", [sa.text("score DESC")])
    op.create_index("idx_prop_rec_expires", "property_recommendations", ["expires_at"])

    op.create_table(
        "room_recommendations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("synced_rooms.id"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("score_breakdown", JSONB()),
        sa.Column("rank", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column("expires_at", sa.DateTime()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "room_id"),
    )
    op.create_index("idx_room_rec_user", "room_recommendations", ["user_id"])
    op.create_index("idx_room_rec_score", "room_recommendations", [sa.text("score DESC")])


def downgrade():
    op.drop_table("room_recommendations")
    op.drop_table("property_recommendations")