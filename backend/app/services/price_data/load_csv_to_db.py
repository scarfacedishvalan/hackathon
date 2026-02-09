"""
Script to load price data from CSV files into a SQLite database.
Reads all CSV files from a folder and creates a single table with Date and Adj Close values.
"""

import pandas as pd
import sqlite3
from pathlib import Path
import os

# Configuration
CSV_FOLDER = r"C:\Python\portfolio-project\data\price_data"
DB_PATH = os.path.join(os.path.dirname(__file__), "price_data.db")
TABLE_NAME = "price_history"


def load_csv_to_dict(csv_folder: str) -> dict:
    """
    Load all CSV files from folder and extract Date and Adj Close columns.
    
    Args:
        csv_folder: Path to folder containing CSV files
        
    Returns:
        Dictionary with ticker as key and DataFrame with Date index and Close price as value
    """
    csv_folder_path = Path(csv_folder)
    price_data = {}
    
    print(f"Scanning folder: {csv_folder}")
    csv_files = list(csv_folder_path.glob("*.csv"))
    print(f"Found {len(csv_files)} CSV files\n")
    
    for csv_file in csv_files:
        ticker = csv_file.stem  # Filename without extension
        
        try:
            # Read CSV file
            df = pd.read_csv(csv_file, parse_dates=['Date'])
            
            # Check for Adj Close or Close column
            if 'Close' in df.columns:
                close_col = 'Close'
            else:
                print(f"⚠ Skipping {ticker}: No 'Adj Close' or 'Close' column found")
                continue
            
            # Extract Date and Close price
            df_clean = df[['Date', close_col]].copy()
            df_clean = df_clean.rename(columns={close_col: ticker})
            df_clean = df_clean.set_index('Date')
            df_clean = df_clean.dropna()
            
            price_data[ticker] = df_clean
            print(f"✓ Loaded {ticker}: {len(df_clean)} rows from {df_clean.index[0].date()} to {df_clean.index[-1].date()}")
            
        except Exception as e:
            print(f"✗ Error loading {ticker}: {e}")
    
    return price_data


def create_combined_dataframe(price_data: dict) -> pd.DataFrame:
    """
    Combine all price data into a single DataFrame with Date index and ticker columns.
    
    Args:
        price_data: Dictionary of DataFrames with ticker as key
        
    Returns:
        Combined DataFrame with Date index and one column per ticker
    """
    print(f"\nCombining {len(price_data)} tickers into single DataFrame...")
    
    # Combine all DataFrames using outer join to keep all dates
    combined_df = pd.concat(price_data.values(), axis=1, join='outer')
    combined_df.columns = price_data.keys()
    
    # Sort by date
    combined_df = combined_df.sort_index()
    
    print(f"Combined DataFrame shape: {combined_df.shape}")
    print(f"Date range: {combined_df.index[0].date()} to {combined_df.index[-1].date()}")
    print(f"Total tickers: {len(combined_df.columns)}")
    
    return combined_df


def save_to_sqlite(df: pd.DataFrame, db_path: str, table_name: str):
    """
    Save DataFrame to SQLite database.
    
    Args:
        df: DataFrame to save
        db_path: Path to SQLite database file
        table_name: Name of the table to create
    """
    print(f"\nSaving to SQLite database: {db_path}")
    
    # Remove existing database if it exists
    if os.path.exists(db_path):
        print(f"Removing existing database: {db_path}")
        os.remove(db_path)
    
    # Create connection and save
    conn = sqlite3.connect(db_path)
    
    try:
        # Reset index to make Date a column
        df_to_save = df.reset_index()
        
        # Save to SQLite
        df_to_save.to_sql(table_name, conn, if_exists='replace', index=False)
        
        print(f"✓ Successfully saved {len(df_to_save)} rows to table '{table_name}'")
        
        # Verify data
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        print(f"✓ Verified: {row_count} rows in database")
        
        # Show table info
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print(f"✓ Table has {len(columns)} columns")
        
    finally:
        conn.close()

def read_from_sqlite(db_path: str=None, table_name: str = TABLE_NAME) -> pd.DataFrame:
    """
    Read data from SQLite database into a DataFrame.
    
    Args:
        db_path: Path to SQLite database file
        table_name: Name of the table to read
    """
    print(f"\nReading from SQLite database: {db_path}")

    if db_path is None:
        #  Go two levels up from current file and look for any .db file
        parent_dir = Path(__file__).parent.parent
        db_files = list(parent_dir.glob("**/*.db"))
        if not db_files:
            raise FileNotFoundError(f"No .db file found in {parent_dir}")
        db_path = db_files[0]  # Use the first .db file found
    
    if not os.path.exists(db_path):
        print(f"✗ Database file not found: {db_path}")
        return pd.DataFrame()
    
    conn = sqlite3.connect(db_path)
    
    try:
        df = pd.read_sql(f"SELECT * FROM {table_name}", conn, parse_dates=['Date'])
        print(f"✓ Successfully read {len(df)} rows from table '{table_name}'")
        return df
    except Exception as e:
        print(f"✗ Error reading from database: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def main():
    """Main execution function."""
    print("=" * 80)
    print("PRICE DATA LOADER - CSV to SQLite")
    print("=" * 80)
    print()
    
    # Step 1: Load CSV files
    price_data = load_csv_to_dict(CSV_FOLDER)
    
    if not price_data:
        print("\n✗ No data loaded. Exiting.")
        return
    
    # Step 2: Combine into single DataFrame
    combined_df = create_combined_dataframe(price_data)
    
    # Step 3: Save to SQLite
    save_to_sqlite(combined_df, DB_PATH, TABLE_NAME)
    
    print()
    print("=" * 80)
    print("✓ COMPLETE")
    print("=" * 80)
    print(f"\nDatabase location: {DB_PATH}")
    print(f"Table name: {TABLE_NAME}")
    print(f"\nTo query the data:")
    print(f"  import sqlite3")
    print(f"  conn = sqlite3.connect('{DB_PATH}')")
    print(f"  df = pd.read_sql('SELECT * FROM {TABLE_NAME}', conn)")


if __name__ == "__main__":
    # main()
    df = read_from_sqlite()
    print(df.head())
