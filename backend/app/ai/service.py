from langchain_core.messages import HumanMessage, SystemMessage

from app.ai.llm import AssistantUnavailable, map_provider_error

MAX_ANSWER_CHARS = 2000
SYSTEM_PROMPT = (
    "You are the business assistant for Suvai, a small food stall business. "
    "You currently have NO access to sales, stock, expense or forecast data. "
    "Never invent numbers. If a question needs data, say the data is not available to you yet. "
    "Keep answers short and practical."
)


def ask(llm, question: str) -> str:
    try:
        reply = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=question)])
    except AssistantUnavailable:
        raise
    except Exception as exc:
        raise map_provider_error(exc) from exc
    text = reply.content.strip() if isinstance(reply.content, str) else ""
    if not text:
        raise AssistantUnavailable(502, "The AI provider returned an empty answer.")
    return text[:MAX_ANSWER_CHARS]