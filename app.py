import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
import os
import gdown

from agent import BIAgent

# -------------------------------
# Load environment variables
# -------------------------------
load_dotenv(override=True)

# -------------------------------
# Download DuckDB database if not present
# -------------------------------
DB_PATH = "instacart.duckdb"

if not os.path.exists(DB_PATH):
    with st.spinner("📥 Downloading Instacart database (first run only)..."):
        gdown.download(
            "https://drive.google.com/uc?id=1cZZnNBZyzG54HXjQvuzCjW25NvnZC3Uj",
            DB_PATH,
            quiet=False,
        )

# -------------------------------
# Streamlit Config
# -------------------------------
st.set_page_config(
    page_title="Instacart BI Agent",
    layout="wide"
)

st.title("🛒 Instacart Conversational BI Agent")

st.markdown(
    """
Ask natural language questions about the 35M+ rows Instacart dataset.

The agent will:
- Generate DuckDB SQL
- Execute the query
- Return results
- Automatically visualize them
"""
)

# -------------------------------
# Initialize Agent
# -------------------------------
if "agent" not in st.session_state:
    try:
        st.session_state.agent = BIAgent()
        st.session_state.messages = []
    except Exception as e:
        st.error(f"❌ Error starting agent: {e}")
        st.stop()

# -------------------------------
# Display Chat History
# -------------------------------
for msg in st.session_state.messages:

    if msg["role"] == "user":

        with st.chat_message("user"):
            st.markdown(msg["content"])

    else:

        with st.chat_message("assistant"):

            if "thinking" in msg:

                with st.expander("Show Agent Reasoning & SQL"):

                    st.markdown("### Thinking")
                    st.write(msg["thinking"])

                    st.markdown("### SQL")
                    st.code(msg["sql"], language="sql")

            if "data" in msg:

                df = msg["data"]

                chart_type = msg.get("chart_type", "table")

                if (
                    chart_type in ["bar", "line", "pie"]
                    and msg.get("x_axis")
                    and msg.get("y_axis")
                ):

                    x = msg["x_axis"]
                    y = msg["y_axis"]

                    try:

                        if chart_type == "bar":

                            fig = px.bar(
                                df,
                                x=x,
                                y=y,
                                title=f"{y} by {x}",
                            )

                            st.plotly_chart(
                                fig,
                                use_container_width=True,
                            )

                        elif chart_type == "line":

                            fig = px.line(
                                df,
                                x=x,
                                y=y,
                                title=f"{y} over {x}",
                            )

                            st.plotly_chart(
                                fig,
                                use_container_width=True,
                            )

                        elif chart_type == "pie":

                            fig = px.pie(
                                df,
                                names=x,
                                values=y,
                                title=f"Distribution of {x}",
                            )

                            st.plotly_chart(
                                fig,
                                use_container_width=True,
                            )

                        with st.expander("View Raw Tabular Data"):

                            st.dataframe(df)

                    except Exception as e:

                        st.error(
                            f"Could not render {chart_type} chart: {e}"
                        )

                        st.dataframe(df)

                else:

                    st.dataframe(df)

# -------------------------------
# User Input
# -------------------------------
user_input = st.chat_input(
    "E.g. Which 5 departments have the highest reorder rate?"
)

if user_input:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_input,
        }
    )

    with st.chat_message("user"):

        st.markdown(user_input)

    with st.chat_message("assistant"):

        with st.spinner(
            "Translating intent, generating SQL and querying DuckDB..."
        ):

            response = (
                st.session_state.agent.process_query(
                    user_input
                )
            )

            if response["status"] == "success":

                msg_data = {

                    "role": "assistant",

                    "thinking": response["thinking"],

                    "sql": response["sql"],

                    "data": response["data"],

                    "chart_type": response["chart_type"],

                    "x_axis": response["x_axis"],

                    "y_axis": response["y_axis"],
                }

                with st.expander(
                    "Show Agent Reasoning & SQL"
                ):

                    st.markdown("### Thinking")

                    st.write(msg_data["thinking"])

                    st.markdown("### SQL")

                    st.code(
                        msg_data["sql"],
                        language="sql",
                    )

                df = msg_data["data"]

                chart_type = msg_data["chart_type"]

                x = msg_data["x_axis"]

                y = msg_data["y_axis"]

                if (
                    chart_type in ["bar", "line", "pie"]
                    and x
                    and y
                ):

                    try:

                        if chart_type == "bar":

                            fig = px.bar(
                                df,
                                x=x,
                                y=y,
                                title=f"{y} by {x}",
                            )

                            st.plotly_chart(
                                fig,
                                use_container_width=True,
                            )

                        elif chart_type == "line":

                            fig = px.line(
                                df,
                                x=x,
                                y=y,
                                title=f"{y} over {x}",
                            )

                            st.plotly_chart(
                                fig,
                                use_container_width=True,
                            )

                        elif chart_type == "pie":

                            fig = px.pie(
                                df,
                                names=x,
                                values=y,
                                title=f"Distribution of {x}",
                            )

                            st.plotly_chart(
                                fig,
                                use_container_width=True,
                            )

                        with st.expander(
                            "View Raw Tabular Data"
                        ):

                            st.dataframe(df)

                    except Exception as e:

                        st.error(
                            f"Could not render chart: {e}"
                        )

                        st.dataframe(df)

                else:

                    st.dataframe(df)

                st.session_state.messages.append(
                    msg_data
                )

            else:

                st.error(response["message"])

