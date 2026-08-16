from dataclasses import dataclass


@dataclass(frozen=True)
class EntityRule:
    entity_type: str
    canonical: str
    aliases: tuple[str, ...]


RULES = (
    EntityRule("process", "申请材料", ("申请材料", "报名材料", "上传资料", "上传文件", "哪些东西")),
    EntityRule("process", "申请状态", ("申请状态", "审核状态", "处理进度", "申请进度", "查进度", "处理到哪")),
    EntityRule("process", "录取结果", ("录取结果", "录取通知", "有没有录取")),
    EntityRule("support", "奖学金", ("奖学金", "资助", "助学金")),
    EntityRule("cost", "学费", ("学费", "收费", "缴费", "多少钱")),
    EntityRule("audience", "国际学生", ("国际学生", "留学生", "外籍学生")),
    EntityRule("audience", "新生", ("新生", "刚入学", "入学学生")),
    EntityRule("field", "计算机", ("计算机", "电脑专业", "计算机科学")),
    EntityRule("field", "人工智能", ("人工智能", "AI方向", "AI专业")),
    EntityRule("field", "软件工程", ("软件工程", "软件开发专业")),
    EntityRule("field", "工程", ("工程专业", "工科", "工程方向")),
    EntityRule("field", "商科", ("商科", "商业专业", "管理类专业")),
)


def extract_entities(query: str) -> list[dict[str, str]]:
    entities = []
    seen = set()
    for rule in RULES:
        matches = sorted((alias for alias in rule.aliases if alias in query), key=len, reverse=True)
        if matches and rule.canonical not in seen:
            entities.append({
                "type": rule.entity_type,
                "value": rule.canonical,
                "matched": matches[0],
            })
            seen.add(rule.canonical)
    return entities


def enhance_query(query: str, entities: list[dict[str, str]]) -> str:
    additions = [entity["value"] for entity in entities if entity["value"] not in query]
    return f"{query} {' '.join(additions)}".strip()
