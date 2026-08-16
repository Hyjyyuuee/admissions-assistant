"""initial schema"""
from alembic import op
import sqlalchemy as sa
revision = "0001"
down_revision = None

def upgrade():
    op.create_table("conversations", sa.Column("id", sa.String(36), primary_key=True), sa.Column("title", sa.String(120), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("knowledge_chunks", sa.Column("id", sa.String(36), primary_key=True), sa.Column("source", sa.String(200), nullable=False), sa.Column("category", sa.String(40), nullable=False), sa.Column("title", sa.String(200), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("entities", sa.Text(), nullable=False))
    op.create_index("ix_knowledge_chunks_source", "knowledge_chunks", ["source"])
    op.create_index("ix_knowledge_chunks_category", "knowledge_chunks", ["category"])
    op.create_table("messages", sa.Column("id", sa.String(36), primary_key=True), sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id"), nullable=False), sa.Column("role", sa.String(16), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("sources", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])

def downgrade():
    op.drop_table("messages"); op.drop_table("knowledge_chunks"); op.drop_table("conversations")

