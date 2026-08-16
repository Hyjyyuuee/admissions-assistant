import re

import httpx
from .config import settings

SYSTEM = """你是 Admissions Assistant 招生助手。只能依据给定资料回答；资料不足时明确说明，并建议联系招生办公室。回答简洁、准确，不编造日期、费用或录取条件。使用中文。请只输出适合微信小程序直接显示的纯文本，不要使用 Markdown，不要使用星号、井号、反引号或 Markdown 表格。"""


def plain_text(text: str) -> str:
    """Remove common Markdown that a WeChat <text> component cannot render."""
    text = re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", text)
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    return text.strip()


def local_answer(context: list[dict], mode: str = "local") -> tuple[str, str]:
    if not context:
        return "暂时没有检索到能回答这个问题的校内资料。请换一种问法，或联系招生办公室确认。", mode
    summary = "\n".join(f"• {item['content']}" for item in context[:3])
    return f"根据现有招生资料：\n{summary}\n\n建议以学校最新官方通知为准。", mode


async def answer(question: str, context: list[dict], history: list[dict]) -> tuple[str, str]:
    context_text = "\n\n".join(f"[{x['title']}] {x['content']}" for x in context)
    if not settings.deepseek_api_key:
        return local_answer(context)
    messages = [{"role": "system", "content": SYSTEM}]
    messages.extend(history[-6:])
    messages.append({"role": "user", "content": f"资料：\n{context_text}\n\n问题：{question}"})
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                f"{settings.deepseek_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
                json={"model": settings.deepseek_model, "messages": messages, "temperature": 0.2},
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return plain_text(content), "deepseek"
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return local_answer(context, "local_fallback")
