from dataclasses import dataclass


CATEGORY_KEYWORDS = {
    "admissions": {
        "申请", "报名", "提交", "材料", "文件", "上传", "审核", "状态", "进度",
        "录取", "结果", "通知", "补充材料", "申请表", "成绩单", "推荐信",
    },
    "faculty": {
        "学院", "专业", "课程", "方向", "培养", "导师", "计算机", "软件工程",
        "人工智能", "数据科学", "工程", "商科", "管理", "金融", "会计",
    },
    "policy": {
        "政策", "奖学金", "资助", "学费", "费用", "缴费", "退款", "住宿费",
        "国际学生", "语言", "签证", "护照", "保险", "认证", "翻译件",
    },
}


@dataclass(frozen=True)
class RouteDecision:
    primary: str
    candidates: tuple[str, ...]
    scores: dict[str, int]
    matched_keywords: dict[str, tuple[str, ...]]


def route_query(query: str) -> RouteDecision:
    matched = {
        category: tuple(sorted(keyword for keyword in keywords if keyword in query))
        for category, keywords in CATEGORY_KEYWORDS.items()
    }
    # Longer phrases carry more intent than broad single concepts. For example,
    # "国际学生" should outweigh the generic word "申请".
    scores = {
        category: sum(max(1, len(keyword) - 1) for keyword in keywords)
        for category, keywords in matched.items()
    }
    best_score = max(scores.values(), default=0)
    if best_score == 0:
        return RouteDecision("general", tuple(CATEGORY_KEYWORDS), scores, matched)

    ordered = sorted(scores, key=lambda category: scores[category], reverse=True)
    # Every positively matched category becomes a callable tool. This lets a
    # query such as "国际学生申请材料" use both Policy and Admissions.
    candidates = tuple(category for category in ordered if scores[category] > 0)
    return RouteDecision(ordered[0], candidates, scores, matched)


def category_multiplier(category: str, decision: RouteDecision) -> float:
    if decision.primary == "general":
        return 1.0
    if category == decision.primary:
        return 1.18
    if category in decision.candidates:
        return 1.08
    return 0.96
