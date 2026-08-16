from dataclasses import dataclass

from sqlalchemy.orm import Session

from .models import KnowledgeChunk
from .router import RouteDecision


@dataclass(frozen=True)
class KnowledgeTool:
    name: str
    category: str
    description: str

    def load(self, db: Session) -> list[KnowledgeChunk]:
        return db.query(KnowledgeChunk).filter(KnowledgeChunk.category == self.category).all()


TOOLS = {
    "admissions": KnowledgeTool(
        name="admissions_kb",
        category="admissions",
        description="申请材料、申请流程、审核状态和录取结果",
    ),
    "faculty": KnowledgeTool(
        name="faculty_kb",
        category="faculty",
        description="学院、专业、课程方向和培养信息",
    ),
    "policy": KnowledgeTool(
        name="policy_kb",
        category="policy",
        description="奖学金、费用和国际学生政策提示",
    ),
}


def select_tools(decision: RouteDecision) -> list[KnowledgeTool]:
    if decision.primary == "general":
        return list(TOOLS.values())
    return [TOOLS[category] for category in decision.candidates if category in TOOLS]


def load_tool_documents(db: Session, tools: list[KnowledgeTool]) -> list[KnowledgeChunk]:
    documents = []
    seen = set()
    for tool in tools:
        for document in tool.load(db):
            if document.id not in seen:
                documents.append(document)
                seen.add(document.id)
    return documents


def tool_manifest() -> list[dict[str, str]]:
    return [
        {"name": tool.name, "category": tool.category, "description": tool.description}
        for tool in TOOLS.values()
    ]
