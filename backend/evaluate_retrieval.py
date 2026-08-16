from .database import SessionLocal
from .entities import enhance_query, extract_entities
from .rag import retrieve
from .router import route_query
from .knowledge_tools import select_tools
from .seed import sync_knowledge


CASES = [
    ("报名时都要上传哪些东西？", {"admissions/application_materials.md"}, "admissions"),
    (
        "交完申请以后怎么知道处理到哪一步了？",
        {"admissions/application_process.md", "admissions/admission_results.md"}, "admissions",
    ),
    ("刚入学的学生有没有资助？", {"policy/scholarships.md"}, "policy"),
    ("计算机方面可以学什么？", {"faculty/computer_science.md"}, "faculty"),
    ("学费要交多少钱？", {"policy/tuition_fees.md"}, "policy"),
    ("国际学生申请要准备什么？", {"policy/international_students.md"}, "policy"),
]


def main() -> int:
    sync_knowledge()
    db = SessionLocal()
    failures = 0
    try:
        for query, expected, expected_route in CASES:
            entities = extract_entities(query)
            enhanced_query = enhance_query(query, entities)
            hits = retrieve(db, enhanced_query)
            route = route_query(enhanced_query)
            tools = select_tools(route)
            sources = []
            for hit in hits:
                if hit["source"] not in sources:
                    sources.append(hit["source"])
            passed = bool(sources) and sources[0] in expected and route.primary == expected_route
            failures += 0 if passed else 1
            mark = "PASS" if passed else "FAIL"
            print(f"[{mark}] {query}")
            print(f"       route: {route.primary} (expected: {expected_route})")
            print(f"       tools: {', '.join(tool.name for tool in tools)}")
            print(f"       entities: {', '.join(entity['value'] for entity in entities) or 'none'}")
            print(f"       graph: {'used' if any(hit.get('graph_score', 0) > 0 for hit in hits) else 'no match'}")
            print(f"       top sources: {', '.join(sources) or 'none'}")
    finally:
        db.close()

    print(f"\nResult: {len(CASES) - failures}/{len(CASES)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
