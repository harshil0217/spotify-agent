#import libraries
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools 
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
import asyncio
from asyncio.exceptions import TimeoutError
import os
from dotenv import load_dotenv
import requests  # Add this for API key validation
import warnings
import json
from pprint import pprint

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
        "firecrawl" : {
            "command": 'npx',
            "args": ['-y', 'firecrawl-mcp'],
            "env": {
                "FIRECRAWL_API_KEY": firecrawl_key
            },
            "transport": "stdio",
            
        },
        "spotify": {
            "command": "uvx",
            "args": [
                "--form",
                "git+https://github.com/varunneal/spotify-mcp",
                "spotify-mcp"
            ],
            "env": {
                "SPOTIFY_CLIENT_ID": os.getenv("SPOTIFY_CLIENT_ID"),
                "SPOTIFY_CLIENT_SECRET": os.getenv("SPOTIFY_CLIENT_SECRET"),
                "SPOTIFY_REDIRECT_URI": os.getenv("SPOTIFY_REDIRECT_URI")
            },
                   
        }
    }     
)
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
    agent_response = await agent.ainvoke({"messages": "Find only one article about the 3 best restaurants in New York City, read the contents but dont output, and tell me what those restaraunts are alongside a quick summary of them."}) 
    
    return agent_response

# Run the function
if __name__ == "__main__":
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
        response = f"An error occurred: {e}"

    pprint(response)