#import libraries
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
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
from typing import Annotated, List, Dict, Any, TypedDict
import streamlit as st
import json


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


# Custom State for Multi-Agent System
class MultiAgentState(TypedDict):
    messages: Annotated[List, "The conversation messages"]
    current_agent: str  # Track which agent should handle the task
    task_type: str      # Type of task: "search", "playlist", or "general"
    search_results: Dict[str, Any]  # Store search results between agents
    playlist_info: Dict[str, Any]   # Store playlist information


def categorize_request(message: str) -> str:
    """Determine which agent should handle the request"""
    message_lower = message.lower()
    
    # Playlist-related keywords
    playlist_keywords = ["playlist", "create", "add tracks", "add songs", "make a playlist"]
    
    # Search-related keywords  
    search_keywords = ["search", "find", "look for", "discover", "track", "song", "artist", "album"]
    
    if any(keyword in message_lower for keyword in playlist_keywords):
        return "playlist"
    elif any(keyword in message_lower for keyword in search_keywords):
        return "search"
    else:
        return "general"


async def create_multi_agent_graph():
    # Create MCP client and load tools
    client = MCPClient.from_config_file("mcp_config.json")
    adapter = LangChainAdapter()
    all_tools = await adapter.create_tools(client)
    
    print(f"Loaded {len(all_tools)} tools from MCP")
    
    # Filter tools by category
    search_tools = [tool for tool in all_tools if tool.name in ["searchSpotify"]]
    playlist_tools = [tool for tool in all_tools if tool.name in [
        "createPlaylist", "addTracksToPlaylist", "getMyPlaylists", "getPlaylistTracks"
    ]]
    
    print(f"Search tools: {[t.name for t in search_tools]}")
    print(f"Playlist tools: {[t.name for t in playlist_tools]}")
    
    # Define LLM
    llm = ChatGroq(model='meta-llama/llama-4-scout-17b-16e-instruct')
    
    # ORCHESTRATOR AGENT
    def orchestrator_agent(state: MultiAgentState):
        """Routes requests to appropriate specialized agents"""
        last_message = state["messages"][-1]
        
        if isinstance(last_message, HumanMessage):
            task_type = categorize_request(last_message.content)
            
            system_msg = """You are an orchestrator agent for a Spotify multi-agent system. 
            
            Available agents:
            - Search Agent: Handles finding tracks, albums, artists on Spotify
            - Playlist Agent: Handles creating playlists and adding tracks to playlists
            
            Based on the user's request, determine which agent should handle the task and provide
            clear instructions to that agent. If the task requires both searching and playlist creation,
            coordinate between the agents.
            
            Task Type Identified: """ + task_type
            
            response = llm.invoke([
                {"role": "system", "content": system_msg},
                {"role": "user", "content": last_message.content}
            ])
            
            return {
                "messages": state["messages"] + [response],
                "task_type": task_type,
                "current_agent": task_type if task_type in ["search", "playlist"] else "orchestrator"
            }
        
        return {"messages": state["messages"]}
    
    # SEARCH AGENT
    def search_agent(state: MultiAgentState):
        """Specialized agent for finding tracks, albums, artists"""
        search_llm = llm.bind_tools(search_tools, parallel_tool_calls=False)
        
        system_msg = """You are a specialist Spotify Search Agent. Your only job is to find tracks, albums, artists, or playlists on Spotify.
        
        Available tools:
        - searchSpotify: Search for tracks, albums, artists, or playlists
        
        When searching:
        - Use appropriate search queries
        - Return detailed information about found items
        - If user wants multiple songs, search for each individually or use broader queries
        - Always provide track URIs/IDs for playlist creation
        
        CRITICAL - Parameter Type Requirements:
        **NUMBERS MUST NEVER HAVE QUOTES**
        - CORRECT: limit: 10
        - WRONG: limit: "10"
        """
        
        recent_messages = state["messages"][-5:]
        response = search_llm.invoke([{"role": "system", "content": system_msg}] + 
                                   [{"role": "user", "content": msg.content} for msg in recent_messages if hasattr(msg, 'content')])
        
        return {"messages": state["messages"] + [response]}
    
    # PLAYLIST AGENT  
    def playlist_agent(state: MultiAgentState):
        """Specialized agent for playlist operations"""
        playlist_llm = llm.bind_tools(playlist_tools, parallel_tool_calls=False)
        
        system_msg = """You are a specialist Spotify Playlist Agent. Your job is to create and manage playlists.
        
        Available tools:
        - createPlaylist: Create a new playlist
        - addTracksToPlaylist: Add tracks to a playlist
        - getMyPlaylists: Get user's playlists
        - getPlaylistTracks: Get tracks from a playlist
        
        When creating playlists:
        - If user doesn't specify size, limit to 10 songs
        - Create descriptive playlist names and descriptions
        - Add appropriate tracks based on the theme/genre requested
        - Always ensure tracks are actually added to created playlists
        
        CRITICAL - Parameter Type Requirements:
        **NUMBERS MUST NEVER HAVE QUOTES**
        - CORRECT: limit: 10  
        - WRONG: limit: "10"
        """
        
        recent_messages = state["messages"][-5:]
        response = playlist_llm.invoke([{"role": "system", "content": system_msg}] + 
                                     [{"role": "user", "content": msg.content} for msg in recent_messages if hasattr(msg, 'content')])
        
        return {"messages": state["messages"] + [response]}

    # AGENT ROUTER
    def route_to_agent(state: MultiAgentState):
        """Route to the appropriate agent based on task type"""
        task_type = state.get("task_type", "general")
        current_agent = state.get("current_agent", "orchestrator")
        
        # Check if we need tools (last message is a tool call)
        last_message = state["messages"][-1] if state["messages"] else None
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tools"
        
        # Route based on current agent
        if current_agent == "search":
            return "search_agent"
        elif current_agent == "playlist":
            return "playlist_agent"
        else:
            return "orchestrator"

    # BUILD THE GRAPH
    builder = StateGraph(MultiAgentState)
    
    # Add agent nodes
    builder.add_node("orchestrator", orchestrator_agent)
    builder.add_node("search_agent", search_agent)  
    builder.add_node("playlist_agent", playlist_agent)
    builder.add_node("tools", ToolNode(search_tools + playlist_tools))
    
    # Define edges
    builder.add_edge(START, "orchestrator")
    
    # Conditional edges from orchestrator
    builder.add_conditional_edges(
        "orchestrator",
        route_to_agent,
        {
            "search_agent": "search_agent",
            "playlist_agent": "playlist_agent", 
            "orchestrator": END,
            "tools": "tools"
        }
    )
    
    # Conditional edges from search agent
    builder.add_conditional_edges(
        "search_agent",
        tools_condition,
        {
            "tools": "tools",
            "__end__": END
        }
    )
    
    # Conditional edges from playlist agent
    builder.add_conditional_edges(
        "playlist_agent", 
        tools_condition,
        {
            "tools": "tools",
            "__end__": END
        }
    )
    
    # Tools always go back to orchestrator for routing
    builder.add_edge("tools", "orchestrator")
    
    return builder.compile()
    



async def invoke_our_graph(agent, st_messages):
    response = await agent.ainvoke({"messages": st_messages})
    return response
    

async def main():
    # Kill any existing processes on port 8090 before starting
    print("Checking for existing processes on port 8090...")
    kill_processes_on_port(8090)
    
    # Create the multi-agent graph
    agent = await create_multi_agent_graph()
    
    config = {"configurable": {"thread_id": 1234}}
    
    print("\n🎵 Multi-Agent Spotify System Ready!")
    print("Available capabilities:")
    print("- Search Agent: Find tracks, albums, artists")
    print("- Playlist Agent: Create and manage playlists")
    print("- Orchestrator: Routes tasks to appropriate agents")
    print("\nType your request (or 'quit' to exit):\n")
    
    while True:
        try:
            message = input("User: ")
            if message.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
                
            # Initialize state for multi-agent system
            initial_state = {
                "messages": [HumanMessage(content=message)],
                "current_agent": "orchestrator",
                "task_type": "general",
                "search_results": {},
                "playlist_info": {}
            }
            
            print("\n🤖 Processing request...\n")
            
            async for event in agent.astream_events(initial_state, version='v2', config=config):
                kind = event["event"]
                if kind == "on_chat_model_stream":
                    addition = event["data"]["chunk"].content
                    print(addition, end='', flush=True)
                elif kind == "on_tool_start":
                    tool_name = event['name']
                    print(f"\n🔧 [Using tool: {tool_name}]")
                elif kind == "on_tool_end":
                    tool_name = event['name'] 
                    print(f"✅ [Tool {tool_name} completed]")
                    
            print("\n" + "="*50 + "\n")
                    
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error occurred: {e}")
            print("Please try again.\n")

            

if __name__ == "__main__":
    # Run the main function in an event loop
    asyncio.run(main())