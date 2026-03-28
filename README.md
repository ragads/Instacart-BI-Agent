# Conversational BI Agent - Instacart Dataset

An AI-powered Business Intelligence agent designed to translate natural language questions into valid DuckDB SQL queries, execute them against an optimized ~35 million row Instacart dataset locally, and intelligently visualize the results.

## Requirements Checklist
- [x] **Load all 6 CSVs and establish relationships**: Accommodated perfectly with `setup_db.py` orchestrating DuckDB ingest pipelines.
- [x] **Accept NLP questions and generate SQL**: Python backend leveraging `gpt-4o` tool-calling converts user intent to robust SQL.
- [x] **Return results as tables/charts**: Streamlit and Plotly Express automatically pick bar, line, pie, or table dependent on query semantics.
- [x] **Handle at least 3-table joins**: Solved via dynamic schema injection.
- [x] **Stretch - Multi-step reasoning**: Prompts optimized for complicated correlations and temporal logic matching domain semantics.
- [x] **Stretch - Conversational memory**: Maintained inside `agent.py`; users can say "now limit to top 5".
- [x] **Stretch - Error recovery**: The logic executes the SQL. If a DuckDB `Exception` triggers (e.g. unknown column), it feeds the trace back safely to the LLM urging a retry (up to 3x).
- [x] **Stretch - Scale Handling**: Implemented by ditching Pandas `.read_csv` and leveraging DuckDB's C++ columnar layout in-memory.

## Architecture Overview

**1. Data Storage & Execution Engine (DuckDB):** 
Instead of loading massive tabular data directly into application memory (Pandas), DuckDB gives us a fast in-process analytical SQL engine. DuckDB runs vectorized execution making it blazingly fast even for the 32M row table. 
   
**2. LLM Core (`agent.py`):** 
Employs standard NLP-to-SQL logic using `openai` SDK (`gpt-4o` or similar). The magic relies on robust Pydantic definitions enforcing strict structured JSON extraction. We actively append actual context (table structure, table constraints) helping the LLM navigate nuances such as NaNs and arbitrary product tree hierarchies. If the LLM generates a bad query, an Error Recovery loop traps the exception and politely requests the LLM to write a better logic statement.

**3. Frontend interface (`app.py`):** 
We use Streamlit strictly to make interaction pleasant. Streamlit easily manages conversational turn-taking, holds the underlying dataframe object inside `session_state`, and orchestrates Plotly interactive data points.

## Key Design Decisions & Tradeoffs

- **DuckDB instead of SQLite/Pandas:** 
  Pandas gets memory-locked parsing 32M records unless manually chunked. SQLite handles 32M rows slowly because it is a row-oriented database optimized for OLTP not OLAP. DuckDB is the ultimate local answer.
- **LLM Selection (OpenAI)**: Used due to their robust Function Calling support, essential for deterministically building `{"chart_type": "...", "sql_query": "..."}` objects every time without prompt-injection risks.
- **Dynamic Semantic Charting**: We explicitly instruct the LLM to choose chart types (`pie`, `bar`, `table`, etc) and map the X and Y bounds directly along with generating SQL. 
- **Time/Temporal Nuances**: The dataset contains `days_since_prior_order`. A huge gotcha is that first-orders register as `NaN`. Instead of cleaning this heavily in Python, we explicitly mention this logic inside the System Prompt for the AI to handle in standard SQL (`COALESCE`, `NULL`).

## Known Limitations and Failure Modes
- **LLM Context Hallucinations:** On particularly ambiguous queries that require chaining 4 tables together without distinct domain terminology, the LLM sometimes hallucinates indirect or fake foreign keys. Our `max_retries` traps syntax failures, but *logical failures* (valid SQL, but mathematically flawed) pass silently.
- **Local Database Pre-Processing**: The codebase relies on running `setup_db.py` first to parse CSV into a standard `.duckdb` instance. This creates another file on disk mimicking disk-latency although it is extremely minute.
- **Cost**: Repeated API usage for GPT-4 over large conversations can incur standard API fees.

## How to Run

1. Clone or extract this repository to a local directory.
2. Ensure you have Python 3.9+ installed natively.
3. Prepare the data: Create a folder named `data/` in the same directory as `app.py`. Extract all 6 Instacart dataset CSVs here:
   - `orders.csv`, `order_products__prior.csv`, `order_products__train.csv`, `products.csv`, `aisles.csv`, `departments.csv`
4. Setup your terminal and environment variables:
   ```bash
   pip install -r requirements.txt
   
   # Rename the environment file
   copy .env.example .env     # (Windows)
   # Or: cp .env.example .env # (Mac/Linux)
   
   # IMPORTANT: Open the new .env file and insert your OPENAI_API_KEY
   ```
5. Pre-compile the local DuckDB Storage:
   ```bash
   python setup_db.py
   ```
   *(Wait about 10-20 seconds. It will convert the raw CSVs into highly responsive queryable indices).*
6. Start the Agent conversational interface:
   ```bash
   streamlit run app.py
   ```
