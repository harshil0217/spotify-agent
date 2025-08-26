from fastapi import FastAPI
from pydantic import BaseModel
from agent_script import create_graph, invoke_our_graph
import asyncio
from contextlib import asynccontextmanager
from typing import List, Dict, Any
from dotenv import load_dotenv


load_dotenv()

#create the agent once at startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.agent = await create_graph()
    yield
    
app = FastAPI(lifespan=lifespan)

class Query(BaseModel):
     input: List[Dict[str, Any]]
    
@app.post("/chat")
async def chat(query: Query):
    agent = app.state.agent
    response = await invoke_our_graph(agent, query.input)
    if agent is None:
        return {"error": "Agent not initialized"}
    print(response)
    return {"response": response}
