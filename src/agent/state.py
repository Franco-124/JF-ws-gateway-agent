from typing import Annotated, Optional, Dict
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    token_usage: Optional[Dict]
    model_id: Optional[str]
    conversation_id: Optional[str]
