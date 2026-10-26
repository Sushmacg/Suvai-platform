import json

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.ai import tools
from app.ai.llm import AssistantUnavailable, map_provider_error

MAX_ANSWER_CHARS = 2000
MAX_TOOL_ROUNDS = 3
SYSTEM_PROMPT = (
    "You are the business assistant for Suvai, a small food stall business. "
    "You have read-only tools for the demand forecast and business analytics. "
    "Only state numbers that come from a tool result. Never invent numbers. "
    "If a tool returns an error or you have no tool for the question, say the data is unavailable. "
    "Forecasts are units expected to sell and may understate demand for products that sell out. "
    "All money amounts are in Indian rupees (use the ₹ symbol, never $). " "Only state dates that appear in a tool result. Round money to the nearest rupee. " "Keep answers short and practical."
)


def _bind(llm):
    binder = getattr(llm, "bind_tools", None)
    if binder is None:
        return llm
    try:
        return binder(tools.TOOL_SCHEMAS)
    except NotImplementedError:
        return llm


def _run_tool(db, call: dict) -> dict:
    return tools.run_tool(db, call.get("name"), call.get("args"))


def ask(llm, question: str, db=None) -> str:
    bound = _bind(llm)
    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=question)]
    try:
        for _ in range(MAX_TOOL_ROUNDS + 1):
            reply = bound.invoke(messages)
            calls = getattr(reply, "tool_calls", None) or []
            if not calls:
                break
            messages.append(reply)
            for call in calls:
                result = json.dumps(_run_tool(db, call), default=str)
                messages.append(ToolMessage(content=result, tool_call_id=call.get("id") or "0"))
        else:
            raise AssistantUnavailable(502, "The assistant could not finish the request.")
    except AssistantUnavailable:
        raise
    except Exception as exc:
        raise map_provider_error(exc) from exc
    text = reply.content.strip() if isinstance(reply.content, str) else ""
    if not text:
        raise AssistantUnavailable(502, "The AI provider returned an empty answer.")
    return text[:MAX_ANSWER_CHARS]