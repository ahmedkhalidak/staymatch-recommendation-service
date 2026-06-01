"""enable pgvector extension and create embedding tables with vector type"""
from alembic import op
import sqlalchemy as sa


revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.drop_table("property_embeddings")
    op.drop_table("user_embeddings")
    op.create_table(
        "property_embeddings",
        sa.Column("property_id", sa.Integer(), sa.ForeignKey("synced_properties.id"), primary_key=True),
        sa.Column("embedding", sa.Text()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint("property_id"),
    )
    op.create_table(
        "user_embeddings",
        sa.Column("user_id", sa.String(255), primary_key=True),
        sa.Column("embedding", sa.Text()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.execute("ALTER TABLE property_embeddings ALTER COLUMN embedding TYPE vector(384) USING embedding::vector")
    op.execute("ALTER TABLE user_embeddings ALTER COLUMN embedding TYPE vector(384) USING embedding::vector")


def downgrade():
    op.execute("ALTER TABLE property_embeddings ALTER COLUMN embedding TYPE TEXT")
    op.execute("ALTER TABLE user_embeddings ALTER COLUMN embedding TYPE TEXT")
    op.drop_table("user_embeddings")
    op.drop_table("property_embeddings")