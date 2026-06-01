"""create interactions and embeddings tables"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_interactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("context", JSONB()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_interactions_user", "user_interactions", ["user_id"])
    op.create_index("idx_interactions_target", "user_interactions", ["target_type", "target_id"])
    op.create_index("idx_interactions_action", "user_interactions", ["action"])
    op.create_index("idx_interactions_created", "user_interactions", ["created_at"])

    op.create_table(
        "property_embeddings",
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("synced_properties.id"), primary_key=True),
        sa.Column("embedding", JSONB()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint("property_id"),
    )

    op.create_table(
        "user_embeddings",
        sa.Column("user_id", sa.String(255), primary_key=True),
        sa.Column("embedding", JSONB()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade():
    op.drop_table("user_embeddings")
    op.drop_table("property_embeddings")
    op.drop_table("user_interactions")