import os
from dotenv import load_dotenv

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from agent_script import invoke_our_graph, create_graph

#from st_callable_util import get_streamlit_cb  # Utility function to get a Streamlit callback handler with context
import asyncio

import time

load_dotenv()  # Load environment variables from a .env file if present

st.title("🎵Spotify Agent🎵")


agent = asyncio.run(create_graph())  # Create the LangGraph agent
 
if "messages" not in st.session_state:
    # default initial message to render in message state
    st.session_state["messages"] = [AIMessage(content="How can I help you?")]
    
    
if "agent" not in st.session_state:
    st.session_state["agent"] = asyncio.run(create_graph())
    
agent = st.session_state["agent"]
    
    
# Loop through all messages in the session state and render them as a chat on every st.refresh mech
for msg in st.session_state.messages:
    # https://docs.streamlit.io/develop/api-reference/chat/st.chat_message
    # we store them as AIMessage and HumanMessage as its easier to send to LangGraph
    if type(msg) == AIMessage:
        st.chat_message("assistant").write(msg.content)
    if type(msg) == HumanMessage:
        st.chat_message("user").write(msg.content)
        

        
# takes new input in chat box from user and invokes the graph
if prompt := st.chat_input():
    st.session_state.messages.append(HumanMessage(content=prompt))
    st.chat_message("user").write(prompt)

    # Process the AI's response and handles graph events using the callback mechanism
    with st.chat_message("assistant"):
        response = asyncio.run(invoke_our_graph(agent, st.session_state.messages))
        text = response["messages"][-1].content
        print(text)
        placeholder = st.empty()
        streamed_text = ""
        for token in text.split():
            streamed_text += token + " "
            placeholder.write(streamed_text)
            time.sleep(0.07)  # Adjust speed as needed

        st.session_state.messages.append(AIMessage(content=text))
