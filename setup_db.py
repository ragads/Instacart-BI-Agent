import duckdb
import os
import time

def setup_database():
    data_dir = "data"
    db_path = "instacart.duckdb"
    
    print(f"Creating DuckDB database at {db_path}...")
    conn = duckdb.connect(db_path)
    
    files = {
        "orders": "orders.csv",
        "order_products_prior": "order_products__prior.csv",
        "order_products_train": "order_products__train.csv",
        "products": "products.csv",
        "aisles": "aisles.csv",
        "departments": "departments.csv"
    }
    
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"Created '{data_dir}' directory. Please place the Kaggle CSV files there.")
        return
        
    for table_name, csv_file in files.items():
        csv_path = os.path.join(data_dir, csv_file)
        if not os.path.exists(csv_path):
            print(f"Warning: {csv_path} not found. Skipping {table_name}. (If running for the first time, drop CSVs in 'data' folder.)")
            continue
            
        print(f"Loading {table_name} from {csv_path} into DuckDB...")
        start_time = time.time()
        # Create table directly from CSV. DuckDB's read_csv_auto is highly parallel and optimized.
        # It handles type inference beautifully, which covers the NaN requirements for 'days_since_prior_order' implicitly in numeric types.
        conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM read_csv_auto('{csv_path}')")
        print(f"Finished {table_name} in {time.time() - start_time:.2f} seconds.")
    
    print("Database setup complete.")
    conn.close()

if __name__ == "__main__":
    setup_database()
