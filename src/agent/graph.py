from langchain_openai import ChatOpenAI
from config import OPENAI_API_KEY
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from agent.state import AgentState
from agent.tools import tools
from agent.prompt import SYSTEM_PROMPT

MODEL_ID = "gpt-4.1-mini"

_model = ChatOpenAI(
    model=MODEL_ID,
    api_key=OPENAI_API_KEY,
).bind_tools(tools)


def _call_model(state: AgentState) -> dict:
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    conversation_id = state.get("conversation_id")
    if conversation_id:
        messages.append(
            SystemMessage(
                content=(
                    "ID de conversacion actual: "
                    f"{conversation_id}. Usa este id al llamar la tool close_conversation_tool."
                )
            )
        )
    messages += state["messages"]
    response = _model.invoke(messages)
    token_usage = getattr(response, "usage_metadata", None)
    return {"messages": [response], "token_usage": token_usage, "model_id": MODEL_ID}


def _should_continue(state: AgentState) -> str:
    if state["messages"][-1].tool_calls:
        return "tools"
    return END


_tool_node = ToolNode(tools)

_builder = StateGraph(AgentState)
_builder.add_node("agent", _call_model)
_builder.add_node("tools", _tool_node)
_builder.set_entry_point("agent")
_builder.add_conditional_edges("agent", _should_continue)
_builder.add_edge("tools", "agent")

graph = _builder.compile()
