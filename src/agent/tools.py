from langchain_core.tools import tool

# Add tools that the agent can use to interact with the user or perform specific actions. For example, a tool to get user information:

@tool
def get_user_information() -> str:
    """Use this tool to get information about the user Johan Franco Alvarez"""
    return """
    Name: Johan Franco Alvarez
    Age: 19
    Occupation: Student
    Interests: Technology, AI, Programming, Music
    """

# Register all available tools
tools = [get_user_information]
