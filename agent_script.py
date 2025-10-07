#import libraries
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import tools_condition, ToolNode
from langgraph.graph import MessagesState
import asyncio
import os
import subprocess
from dotenv import load_dotenv
from mcp_use.client import MCPClient
from mcp_use.adapters.langchain_adapter import LangChainAdapter
import requests
from typing import Annotated, List
import streamlit as st


# Load environment variables
load_dotenv()


def kill_processes_on_port(port):
    """Kill all processes running on the specified port"""
    try:
        # Find processes using the port
        result = subprocess.run(['lsof', '-ti', f':{port}'], 
                              capture_output=True, text=True, check=False)
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            print(f"Found processes on port {port}: {pids}")
            
            # Kill each process
            for pid in pids:
                if pid:
                    try:
                        subprocess.run(['kill', '-9', pid], check=True)
                        print(f"Killed process {pid} on port {port}")
                    except subprocess.CalledProcessError:
                        print(f"Failed to kill process {pid}")
        else:
            print(f"No processes found on port {port}")
            
    except FileNotFoundError:
        print("lsof command not found, trying alternative method...")
        try:
            # Alternative method using netstat and kill
            result = subprocess.run(['netstat', '-tulpn'], 
                                  capture_output=True, text=True, check=False)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if f':{port}' in line and 'LISTEN' in line:
                        parts = line.split()
                        if len(parts) > 6 and '/' in parts[6]:
                            pid = parts[6].split('/')[0]
                            try:
                                subprocess.run(['kill', '-9', pid], check=True)
                                print(f"Killed process {pid} on port {port}")
                            except subprocess.CalledProcessError:
                                print(f"Failed to kill process {pid}")
        except Exception as e:
            print(f"Error killing processes on port {port}: {e}")


# Validate OpenAI API key
openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set.")






'''
brave_server_params = StdioServerParameters(
    command='npx',
    args=['-y', '@modelcontextprotocol/server-brave-search'],
    env={
        "BRAVE_API_KEY": brave_key
    })
'''
'''
client = MultiServerMCPClient(
    {
        # "firecrawl": {
        #     "command": 'npx',
        #     "args": ['-y', 'firecrawl-mcp'],
        #     "env": {
        #         "FIRECRAWL_API_KEY": firecrawl_key
        #     },
        #     "transport": "stdio"
        # },
        "brave-search": {
            "command": 'npx',
            "args": ['-y', 'brave-search-mcp'],
            "env": {
                "BRAVE_API_KEY": brave_key
            },
            "transport": "stdio"
        },
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
        },
        "weather": {
            "command": "npx",
            "args": ["-y", "@timlukahorstmann/mcp-weather"],
            "env": {
                "ACCUWEATHER_API_KEY": "your_api_key_here"
            },
            "transport": "stdio"
        }
    }
)
'''

# Global dictionary to store IP and location data
location_context = {
    "user_ip": None,
    "location_ready": False,
    "detection_attempted": False,
    "city": None,
    "country": None,
}

def detect_ip_node(state: MessagesState):
    """Automatically detect user's public IP"""
    try:
        response = requests.get('https://api.ipify.org?format=json')
        ip_data = response.json()
        # Store in global dictionary
        location_context.update({
            "user_ip": ip_data['ip'],
            "location_ready": True,
            "detection_attempted": True
        })
    except Exception as e:
        # Just proceed without IP if detection fails
        return {
            **state,
            "user_ip": None,
            "location_ready": False
        }
        
    if location_context["user_ip"]:
        print(f"Detected User IP: {location_context['user_ip']}")
        # Use API to fetch city, country of IP
        try:
            response = requests.get(f'https://api.ip2location.io/?key=09DB39B7D0F0287A4D0826261434609A&ip={location_context["user_ip"]}&format=json')
            location_data = response.json()
            print(f"Location Data: {location_data}")
            location_context["city"] = location_data.get("city_name")
            location_context["country"] = location_data.get("country_name")
            print(f"Detected Location: {location_context['city']}, {location_context['country']}")
        except Exception as e:
            print(f"Failed to fetch location data: {e}")
            
@tool
async def get_locataion() -> str:
    """Automatically detect user's public IP"""
    ip = ""
    try:
        response = requests.get('https://api.ipify.org?format=json')
        ip_data = response.json()
        ip = ip_data['ip']
    except Exception as e:
        return "Failed to detect IP address."
    
    """Use API to fetch city, country of IP"""
    try:
        response = requests.get(f'https://api.ip2location.io/?key=09DB39B7D0F0287A4D0826261434609A&ip={ip}&format=json')
        location_data = response.json()
        city = location_data.get("city_name", "Unknown City")
        country = location_data.get("country_name", "Unknown Country")
        print(f"Detected Location: {city}, {country}")
        return f"Detected Location: {city}, {country}"

    except Exception as e:
        return f"Failed to fetch location data: {e}"
    


    

    
async def create_graph():
    
    #create client
    client = MCPClient.from_config_file("mcp_config.json")
    
    # Create adapter instance
    adapter = LangChainAdapter()
    
    #load in tools from the MCP client
    tools = await adapter.create_tools(client)
    
    #select only search and playlist tools
    #tools = [tool for tool in tools if tool.name in ["SpotifyPlaylist", "SpotifySearch"]]
    
    #define llm
    llm = ChatGroq(model='meta-llama/llama-4-scout-17b-16e-instruct')
    
    #bind tools
    llm_with_tools = llm.bind_tools(tools, parallel_tool_calls=False)
    
    #define system prompth
    system_msg = """You are a helpful assistant that has access to Spotify. You can create playlists, find songs, and provide music recommendations.

    When creating playlists:
    - If the user does not specify playlist size, limit playlist lengths to only 10 songs
    - Always provide helpful music recommendations based on user preferences and create well-curated playlists with appropriate descriptions
    - When the User requests a playlist to be created, ensure that there are actually songs added to the playlist you create

    CRITICAL - Parameter Type Requirements:

    **NUMBERS MUST NEVER HAVE QUOTES**
    When you need to pass a number parameter:
    - CORRECT: limit: 10
    - WRONG: limit: "10"

   """
    #define assistant
    def assistant(state: MessagesState):
        #get las user message
        recent_messages = state["messages"][-10:]  # Adjust as needed
        return {"messages": [llm_with_tools.invoke([system_msg] + state["messages"])]}
    
    # Graph
    builder = StateGraph(MessagesState) 

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
    



async def invoke_our_graph(agent, st_messages):
    response = await agent.ainvoke({"messages": st_messages})
    return response
    

async def main():
    # Kill any existing processes on port 8090 before starting
    print("Checking for existing processes on port 8090...")
    kill_processes_on_port(8090)
    
    agent = await create_graph()
    
    
    config = {"configurable": {"thread_id":1234}}
    while True:
        final_text = ""
        message = input("User: ")
        async for event in agent.astream_events({"messages": [message]}, version = 'v2', config=config):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                addition = event["data"]["chunk"].content
                final_text += addition
                print(addition, end='', flush=True)
            elif kind == "on_tool_start":
                print(f"\n[Calling tool: {event['name']}]")
            elif kind == "on_tool_end":
                print(f"\n[Tool {event['name']} completed]")

            

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