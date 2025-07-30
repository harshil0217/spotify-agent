#import libraries
from typing import List
from typing import Annotated
from typing_extensions import TypedDict
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools 
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.prompts import load_mcp_prompt
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import tools_condition, ToolNode
from langgraph.graph import MessagesState
import asyncio
from asyncio.exceptions import TimeoutError
import os
from dotenv import load_dotenv
import requests  # Add this for API key validation
import warnings
import json
from pprint import pprint
import traceback


# Load environment variables
load_dotenv()

# Validate Brave API key
brave_key = os.getenv("BRAVE_API_KEY")
if not brave_key:
    raise ValueError("BRAVE_API_KEY environment variable is not set.")



# Validate OpenAI API key
openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set.")

firecrawl_key = os.getenv("FIRECRAWL_API_KEY")
if not firecrawl_key:
    raise ValueError("FIRECRAWL_API_KEY environment variable is not set.")


# Initialize the model
model = ChatOpenAI(model="gpt-4o")

'''
brave_server_params = StdioServerParameters(
    command='npx',
    args=['-y', '@modelcontextprotocol/server-brave-search'],
    env={
        "BRAVE_API_KEY": brave_key
    })
'''
client = MultiServerMCPClient(
    {
        # "firecrawl" : {
        #     "command": 'npx',
        #     "args": ['-y', 'firecrawl-mcp'],
        #     "env": {
        #         "FIRECRAWL_API_KEY": firecrawl_key
        #     },
        #     "transport": "stdio"
        # },
        
        # "brave-search": {
        #     "command": 'npx',
        #     "args": ['-y', 'brave-search-mcp'],
        #     "env": {
        #         "BRAVE_API_KEY": brave_key
        #     },
        #     "transport": "stdio"
        # },
        "spotify": {
            "command": "uvx",
            "args": [
                "--from",
                "git+https://github.com/varunneal/spotify-mcp",
                "spotify-mcp"
            ],
            "env": {
                "SPOTIFY_CLIENT_ID": os.getenv("SPOTIFY_CLIENT_ID"),
                "SPOTIFY_CLIENT_SECRET": os.getenv("SPOTIFY_CLIENT_SECRET"),
                "SPOTIFY_REDIRECT_URI": os.getenv("SPOTIFY_REDIRECT_URI")
            },
            "transport": "stdio"
        }
    }     
)

async def create_graph():
    
    #define llm
    llm = ChatOpenAI(model="gpt-4o")
    
    #load in tools from the MCP client
    tools = await client.get_tools()
    
    #bind tools
    
    llm_with_tools = llm.bind_tools(tools)
    
    #define system prompt
    system_msg = "You are a helpful assistant that can use various tools to answer questions.  \
                   You can search the web, access a database, and interact with Spotify to find music"
                   
    
    #define assistant
    def assistant(state: MessagesState):
        return {"messages": [llm_with_tools.invoke( system_msg + state["messages"])]}
    
    # Graph
    builder = StateGraph(MessagesState) 
    
    # Define nodes: these do the work
    builder.add_node("assistant", assistant)
    builder.add_node("tools", ToolNode(tools))
    
    # Define nodes: these do the work
    builder.add_node("assistant", assistant)
    builder.add_node("tools", ToolNode(tools))

    # Define edges: these determine the control flow
    builder.add_edge(START, "assistant")
    builder.add_conditional_edges(
        "assistant",
        # If the latest message (result) from assistant is a tool call -> tools_condition routes to tools
        # If the latest message (result) from assistant is a not a tool call -> tools_condition routes to END
        tools_condition,
    )
    builder.add_edge("tools", "assistant")
    graph = builder.compile()
    
    return graph


async def main():
    config = {"configurable": {"thread_id":1234}}
    
    agent = await create_graph()
    
    while True:
        message = input("User: ")
        response = await agent.ainvoke({"messages": [message]}, config=config)
        print("Assistant:", response["messages"][-1].content)

if __name__ == "__main__":
    # Run the main function in an event loop
    asyncio.run(main())
    
    
'''

async def create_graph(firecrawl_session):  # Removed spotify_session
    llm = ChatOpenAI(model="gpt-4o")
    
    firecrawl_tools = await load_mcp_tools(firecrawl_session)
    
    # spotify_tools = await load_mcp_tools(spotify_session)
    
    tools = firecrawl_tools  # + spotify_tools
    llm_with_tools = llm.bind_tools(tools)
    
    #firecrawl_system_prompt = await load_mcp_prompt(firecrawl_session, "system_prompt")
    # spotify_system_prompt = await load_mcp_prompt("spotify", "system_prompt")
    system_prompt = "You are a helpful assistant that can use various tools to answer questions.  \
                   You can search the web, access a database, and interact with Spotify to find music"
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("messages")
    ])
    
    chat_llm = prompt_template | llm_with_tools
    
    # State Management
    class State(TypedDict):
        messages: Annotated[List[AnyMessage], add_messages]
        
    def chat_node(state: State) -> State:
        state["messages"] = chat_llm.invoke({"messages": state["messages"]})
        return state

    # Building the graph
    graph_builder = StateGraph(State)
    graph_builder.add_node("chat_node", chat_node)
    graph_builder.add_node("tool_node", ToolNode(tools=tools))
    graph_builder.add_edge(START, "chat_node")
    graph_builder.add_conditional_edges("chat_node", tools_condition, {"tools": "tool_node", "__end__": END})
    graph_builder.add_edge("tool_node", "chat_node")
    graph = graph_builder.compile(checkpointer=MemorySaver())
    return graph





'''
'''
warnings.filterwarnings("ignore", category=ResourceWarning)
    
async def run_agent():
    #get tools from the MCP client
    tools = await client.get_tools()
   
    # Create agent
    agent = create_react_agent(
        model=model,
        tools=tools,
    )
    
    # Invoke agent
    agent_response = await agent.ainvoke({"messages": "Find 10 songs about the ocean and create a playlist with them."}) 
    
    return agent_response

# Test Spotify API access
def test_spotify_api():
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")

    # Step 1: Get access token using Client Credentials Flow
    auth_response = requests.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
    )
    if auth_response.status_code != 200:
        print("Failed to get Spotify access token:", auth_response.text)
        return False

    access_token = auth_response.json().get("access_token")
    if not access_token:
        print("No access token received from Spotify.")
        return False
    
    return True

# Run the function
if __name__ == "__main__":
    if not test_spotify_api():
        print("Spotify API test failed. Check your credentials.")
        exit(1)
    """
Using asyncio.get_event_loop() with run_until_complete instead of asyncio.run()
because stdio_client launches a persistent MCP server subprocess via npx.

This subprocess communicates asynchronously over stdin/stdout pipes and remains
alive during the client session. A persistent event loop ensures these pipes
stay open and managed properly throughout the agent's execution.

Using asyncio.run() would create and close the loop automatically, which could
cause premature termination of the pipes, leading to I/O errors such as:
'ValueError: I/O operation on closed pipe'.

Maintaining control of the event loop prevents these issues by keeping async I/O
stable for the full duration of interaction with the MCP subprocess and any
external API calls it makes (e.g., Brave Search).
"""

    loop = asyncio.get_event_loop()
    try:
        response = loop.run_until_complete(asyncio.wait_for(run_agent(), timeout=120))
    except TimeoutError:
        response = "The operation timed out."
    except Exception as e:
        traceback.print_exc()
        response = f"An error occurred: {e}"

    pprint(response)

'''

# TO DO: add brave search api, add logic that tells langgraph to go article by article, scrape with firecrawl article by article, and pass that to the chat node,
# research adding chunking node