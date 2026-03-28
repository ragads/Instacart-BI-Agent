import os
import json
import duckdb
import pandas as pd
from typing import Optional, List, Dict, Any
from openai import OpenAI

class BIAgent:
    def __init__(self, db_path="instacart.duckdb"):
        self.db_path = db_path
        self.schema_info = self._get_schema()
        self.chat_history = []
        
        # Using Pollinations.ai free standard endpoint
        self.client = OpenAI(
            api_key="anything",
            base_url="https://text.pollinations.ai/openai/"
        )
        
    def _get_schema(self) -> str:
        """Extract schema dynamically from DuckDB."""
        if not os.path.exists(self.db_path):
            return "Database not found."
            
        conn = duckdb.connect(self.db_path, read_only=True)
        try:
            tables_df = conn.execute("SHOW TABLES").df()
            if tables_df.empty:
                return "Database has no tables."
                
            schema_text = "Database Schema:\n\n"
            for _, row in tables_df.iterrows():
                table = row['name']
                columns_df = conn.execute(f"PRAGMA table_info('{table}')").df()
                schema_text += f"Table: {table}\n"
                for _, col_row in columns_df.iterrows():
                    schema_text += f"  - {col_row['name']} ({col_row['type']})\n"
                schema_text += "\n"
                
            schema_text += "\nAdditional Context:\n"
            schema_text += "1. 'order_products_prior' contains ~32M rows. Always use aggregations or LIMIT.\n"
            schema_text += "2. The 'eval_set' column defines splits.\n"
            schema_text += "3. Product Hierarchy: product -> aisle (via aisle_id) -> department.\n"
            schema_text += "4. Handle NaNs in 'days_since_prior_order' for the first order.\n"
            
            return schema_text
        except Exception as e:
            return f"Error retrieving schema: {e}"
        finally:
            conn.close()
            
    def process_query(self, user_input: str) -> Dict[str, Any]:
        """Process user natural language query using standard OpenAI syntax but overriding backing"""
        
        if "Database not found" in self.schema_info or "no tables" in self.schema_info:
             return {"status": "error", "message": self.schema_info}
             
        max_retries = 3
        last_error = None
        attempt = 0
        
        system_prompt = f"""You are an expert Data Analyst capable of executing DuckDB SQL.
{self.schema_info}

When given a user query:
1. Formulate perfectly valid DuckDB SQL matching their intent.
2. Decide on the best visualization ('bar', 'line', 'pie', 'table').
3. YOU MUST return ONLY a JSON response format representing your logic. Wrap it in a JSON block!
DO NOT respond with anything other than this exact JSON structure:
{{
    "thinking": "Step by step reasoning...",
    "sql_query": "SELECT ... LIMIT 100",
    "chart_type": "bar",
    "x_axis": "column name for x",
    "y_axis": "column name for y"
}}
"""

        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        for msg in self.chat_history:
            messages.append(msg)
                
        messages.append({"role": "user", "content": user_input})

        while attempt < max_retries:
            try:
                current_messages = list(messages)
                if last_error:
                    current_messages.append({
                        "role": "user", 
                        "content": f"The previous SQL query failed exactly with this error: {last_error}\nPlease fix the DuckDB SQL query and return a valid JSON block again."
                    })
                
                # Using standard OpenAI syntax to map to Pollinations.ai backend models
                response = self.client.chat.completions.create(
                    model="openai",
                    messages=current_messages,
                    temperature=0.1
                )
                
                text_response = response.choices[0].message.content.strip()
                
                # Strip markdown JSON fences logically
                if "```json" in text_response:
                    text_response = text_response.split("```json")[1].split("```")[0].strip()
                elif "```" in text_response:
                    text_response = text_response.split("```")[1].split("```")[0].strip()
                    
                plan = json.loads(text_response)
                
                sql_query = plan.get("sql_query", "")
                df = self._execute_sql(sql_query)
                
                # Save into memory
                self.chat_history.append({"role": "user", "content": user_input})
                self.chat_history.append({"role": "assistant", "content": f"Executed SQL successfully:\n{sql_query}"})
                
                return {
                    "status": "success",
                    "thinking": plan.get("thinking", ""),
                    "sql": sql_query,
                    "data": df,
                    "chart_type": plan.get("chart_type", "table"),
                    "x_axis": plan.get("x_axis", None),
                    "y_axis": plan.get("y_axis", None)
                }

            except json.JSONDecodeError as e:
                last_error = f"Failed to parse JSON structure precisely. Response was: {text_response}"
                attempt += 1
            except Exception as e:
                last_error = str(e)
                attempt += 1
                
        return {
            "status": "error",
            "message": f"Failed executing query after {max_retries} attempts.\nLast error: {last_error}"
        }

    def _execute_sql(self, sql: str) -> pd.DataFrame:
        conn = duckdb.connect(self.db_path, read_only=True)
        try:
            df = conn.execute(sql).df()
            return df
        finally:
            conn.close()
