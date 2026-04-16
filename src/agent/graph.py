from langchain_openai import ChatOpenAI
from config import OPENAI_API_KEY
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from agent.state import AgentState
from agent.tools import tools
from agent.prompt import SYSTEM_PROMPT

_model = ChatOpenAI(
    model="gpt-4.1-mini",
    api_key=OPENAI_API_KEY,
).bind_tools(tools)


def _call_model(state: AgentState) -> dict:
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = _model.invoke(messages)
    return {"messages": [response]}


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
