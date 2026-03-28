import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
import os

from agent import BIAgent

# Load environment logic
load_dotenv(override=True)

st.set_page_config(page_title="Instacart BI Agent", layout="wide")

st.title("🛒 Instacart Conversational BI Agent")
st.markdown("Ask natural language questions about the 35M+ rows Instacart dataset. I will generate SQL, execute it locally with DuckDB, and chart the results in real-time.")

if "agent" not in st.session_state:
    try:
        st.session_state.agent = BIAgent()
        st.session_state.messages = []
    except Exception as e:
        st.error(f"Error starting agent: {e}")
        st.stop()

# Display historical chat messages
for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant"):
            if "thinking" in msg:
                with st.expander("Show Agent Reasoning & SQL"):
                    st.markdown("**Thinking:**")
                    st.write(msg["thinking"])
                    st.markdown("**Executed SQL:**")
                    st.code(msg["sql"], language="sql")
            
            if "data" in msg:
                df = msg["data"]
                
                # Render optimal chart dynamically based on tool calling
                chart_type = msg.get("chart_type", "table")
                
                if chart_type in ["bar", "line", "pie"] and msg.get("x_axis") and msg.get("y_axis"):
                    x = msg["x_axis"]
                    y = msg["y_axis"]
                    
                    try:
                        if chart_type == "bar":
                            fig = px.bar(df, x=x, y=y, title=f"{y} by {x}")
                            st.plotly_chart(fig, use_container_width=True)
                        elif chart_type == "line":
                            fig = px.line(df, x=x, y=y, title=f"{y} over {x}")
                            st.plotly_chart(fig, use_container_width=True)
                        elif chart_type == "pie":
                            fig = px.pie(df, names=x, values=y, title=f"Distribution of {x}")
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with st.expander("View Raw Tabular Data"):
                            st.dataframe(df)
                    except Exception as e:
                        st.error(f"Could not render {chart_type} chart: {e}")
                        st.dataframe(df) # Fallback to grid view
                else:
                    st.dataframe(df)

# Handle new user chat explicitly
user_input = st.chat_input("E.g., Which 5 departments have the highest reorder rate?")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
        
    with st.chat_message("assistant"):
        with st.spinner("Translating intent, formulating analytical SQL, and querying DuckDB..."):
            response = st.session_state.agent.process_query(user_input)
            
            if response["status"] == "success":
                msg_data = {
                    "role": "assistant",
                    "thinking": response["thinking"],
                    "sql": response["sql"],
                    "data": response["data"],
                    "chart_type": response["chart_type"],
                    "x_axis": response["x_axis"],
                    "y_axis": response["y_axis"]
                }
                
                # Render inline without waiting for rerun
                with st.expander("Show Agent Reasoning & SQL"):
                    st.markdown("**Thinking:**")
                    st.write(msg_data["thinking"])
                    st.markdown("**Executed SQL:**")
                    st.code(msg_data["sql"], language="sql")
                
                df = msg_data["data"]
                chart_type = msg_data["chart_type"]
                x = msg_data["x_axis"]
                y = msg_data["y_axis"]
                
                if chart_type in ["bar", "line", "pie"] and x and y:
                    try:
                        if chart_type == "bar":
                            fig = px.bar(df, x=x, y=y, title=f"{y} by {x}")
                            st.plotly_chart(fig, use_container_width=True)
                        elif chart_type == "line":
                            fig = px.line(df, x=x, y=y, title=f"{y} over {x}")
                            st.plotly_chart(fig, use_container_width=True)
                        elif chart_type == "pie":
                            fig = px.pie(df, names=x, values=y, title=f"Distribution of {x}")
                            st.plotly_chart(fig, use_container_width=True)
                            
                        with st.expander("View Raw Tabular Data"):
                            st.dataframe(df)
                    except Exception as e:
                        st.error(f"Could not render {chart_type} chart: {e}")
                        st.dataframe(df)
                else:
                    st.dataframe(df)
                    
                st.session_state.messages.append(msg_data)
                
            else:
                st.error(response["message"])
