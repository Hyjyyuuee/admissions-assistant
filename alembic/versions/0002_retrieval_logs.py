"""add retrieval logs"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"


def upgrade():
    if "retrieval_logs" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "retrieval_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("enhanced_query", sa.Text(), nullable=False),
        sa.Column("route", sa.String(40), nullable=False),
        sa.Column("tools", sa.Text(), nullable=False),
        sa.Column("entities", sa.Text(), nullable=False),
        sa.Column("sources", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_retrieval_logs_conversation_id", "retrieval_logs", ["conversation_id"])
    op.create_index("ix_retrieval_logs_route", "retrieval_logs", ["route"])


def downgrade():
    op.drop_index("ix_retrieval_logs_route", table_name="retrieval_logs")
    op.drop_index("ix_retrieval_logs_conversation_id", table_name="retrieval_logs")
    op.drop_table("retrieval_logs")
