import pandas as pd

import numpy as np
from numpy import *
import os
from datetime import datetime, timedelta
import pandas as pd
import sqlite3
from pathlib import Path

RAW_PRICE_DATAPATH = "price_data.xlsx"
USE_EXCEL_DATA = False  # Set to True to use Excel file instead of synthetic data
USE_DB_DATA = True  # Set to True to read from SQLite database instead of Excel or synthetic data
TABLE_NAME = "price_history"


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


class PriceData:
    def __init__(self, df = None, periods = 365, asset_list = None, start_date=None, end_date=None):
        self.asset_list = asset_list
        self.start_date = start_date or (datetime.now() - timedelta(days=5*365)).strftime('%Y-%m-%d')
        self.end_date = end_date or datetime.now().strftime('%Y-%m-%d')
        
        if df is None:
            self._data_src = RAW_PRICE_DATAPATH
            self._datecol = "Date"
            self._dfraw = self.read_prices()
        else:
            self._dfraw = df
        self._periods = periods
        self._returnsdf = self.get_returns()
        if asset_list:
            self._dfraw = pd.DataFrame(self._dfraw[asset_list])
            self._returnsdf = self.get_returns()
    
    def process_data(self, df, append_missing_dates=True):
        #  Drop rows with all missing values
        df = df.dropna(how='any')
        # If append_missing_dates is True, extend data to today using historical random walk
        if append_missing_dates:
            last_date = df.index[-1]
            today = pd.to_datetime(datetime.now().strftime('%Y-%m-%d'))
            if last_date < today:
                print(f"Extending data from {last_date.date()} to {today.date()}...")
                df = PriceData.extend_dataframe_to_today(df, today)
        return df

    def read_prices(self):
        """Fetch price data from Excel file or generate synthetic data."""
        if USE_EXCEL_DATA:
            # Read from Excel file
            try:
                price_df = pd.read_excel(self._data_src, index_col=self._datecol, parse_dates=True)
                # Drop rows with missing values
                price_df.dropna(inplace=True)
                print(f"✓ Successfully read {len(price_df)} rows from Excel file '{self._data_src}'")
                if self.asset_list:
                    price_df = price_df[self.asset_list]
                return price_df
            except FileNotFoundError:
                print(f"Warning: Excel file {self._data_src} not found. Generating synthetic data.")
                return self.generate_synthetic_prices()
        elif USE_DB_DATA:
            # Read from SQLite database
            try:
                price_df = read_from_sqlite()
                price_df.set_index('Date', inplace=True)
                if self.asset_list:
                    price_df = price_df[self.asset_list]
                price_df = self.process_data(price_df, append_missing_dates=True)
                return price_df
            except Exception as e:
                print(f"Warning: Error reading from database: {e}. Generating synthetic data.")
                return self.generate_synthetic_prices()
        else:
            # Generate synthetic data (default)
            return self.generate_synthetic_prices()
    
    def generate_synthetic_prices(self):
        """Generate synthetic price data using random walk with drift."""
        if not self.asset_list:
            raise ValueError("asset_list must be provided to generate synthetic data")
        
        print(f"Generating synthetic data for {len(self.asset_list)} assets...")
        
        # Parse dates
        start = pd.to_datetime(self.start_date)
        end = pd.to_datetime(self.end_date)
        
        # Generate daily dates
        date_range = pd.date_range(start=start, end=end, freq='D')
        n_days = len(date_range)
        
        price_data = {}
        
        for ticker in self.asset_list:
            # Set random seed based on ticker for reproducibility
            np.random.seed(hash(ticker) % (2**32))
            
            # Random walk parameters
            initial_price = np.random.uniform(50, 500)  # Initial price
            drift = np.random.uniform(0.0001, 0.0005)  # Daily drift (positive trend)
            volatility = np.random.uniform(0.015, 0.025)  # Daily volatility
            
            # Generate random walk
            returns = np.random.normal(drift, volatility, n_days)
            price_series = initial_price * np.exp(np.cumsum(returns))
            
            price_data[ticker] = price_series
        
        # Create DataFrame
        price_df = pd.DataFrame(price_data, index=date_range)
        
        print(f"Generated {len(price_df)} days of synthetic data from {price_df.index[0].date()} to {price_df.index[-1].date()}")
        
        return price_df

    def get_assets(self):
        return list(set(self._dfraw.columns))
    
    @staticmethod
    def extend_series_to_today(series: pd.Series, end_date: datetime = None) -> pd.Series:
        """
        Extend a single price series to today's date using a realistic random walk
        calibrated from the historical data's drift and volatility.
        
        Args:
            series: A pandas Series with DatetimeIndex and price values (NaN-free)
            end_date: Target end date. Defaults to today.
            
        Returns:
            Extended pandas Series from original start to end_date
        """
        if end_date is None:
            end_date = pd.to_datetime(datetime.now().strftime('%Y-%m-%d'))
        
        # Drop NaN and sort
        series = series.dropna().sort_index()
        
        if len(series) < 2:
            return series
        
        last_date = series.index[-1]
        if last_date >= end_date:
            return series  # Already up to date
        
        # Calculate historical daily log returns
        log_returns = np.log(series / series.shift(1)).dropna()
        
        # Estimate drift and volatility from historical data
        hist_drift = log_returns.mean()
        hist_vol = log_returns.std()
        
        # Generate dates to fill
        new_dates = pd.date_range(start=last_date + timedelta(days=1), end=end_date, freq='B')  # Business days
        
        if len(new_dates) == 0:
            return series
        
        n_days = len(new_dates)
        last_price = series.iloc[-1]
        
        # Generate random walk with historical drift and volatility
        np.random.seed(hash(series.name) % (2**32) if series.name else 42)
        random_returns = np.random.normal(hist_drift, hist_vol, n_days)
        
        # Build forward prices
        new_prices = last_price * np.exp(np.cumsum(random_returns))
        
        # Create extended series
        extension = pd.Series(new_prices, index=new_dates, name=series.name)
        
        return pd.concat([series, extension])
    
    @staticmethod
    def extend_dataframe_to_today(df: pd.DataFrame, end_date: datetime = None) -> pd.DataFrame:
        """
        Extend all columns of a DataFrame with DatetimeIndex to today's date.
        Each column is extended independently using its own historical drift and volatility.
        
        Args:
            df: DataFrame with DatetimeIndex and price columns
            end_date: Target end date. Defaults to today.
            
        Returns:
            Extended DataFrame with all columns filled to end_date
        """
        if end_date is None:
            end_date = pd.to_datetime(datetime.now().strftime('%Y-%m-%d'))
        
        extended_columns = {}
        
        for col in df.columns:
            series = df[col].dropna()
            if len(series) < 2:
                print(f"⚠ Skipping {col}: insufficient data ({len(series)} rows)")
                extended_columns[col] = series
                continue
            
            extended = PriceData.extend_series_to_today(series, end_date)
            extended_columns[col] = extended
        
        # Combine back into a DataFrame
        result = pd.DataFrame(extended_columns)
        result = result.sort_index()
        
        original_end = df.index[-1].date()
        new_end = result.index[-1].date()
        
        if original_end < new_end:
            print(f"✓ Extended {len(df.columns)} columns from {original_end} to {new_end} "
                  f"(+{len(result) - len(df)} rows)")
        
        return result
    
    def get_returns(self):
        return self._dfraw.astype("float").pct_change(periods=int(self._periods)).fillna(0)
        
    def get_time_period(self):
        length = pd.to_datetime(list(self._dfraw.index)[-1])- pd.to_datetime(list(self._dfraw.index)[0])
        length = length.days/365
        return length
    
    def get_summary_returns(self):
        length = self.get_time_period()
        returns = np.log((self._dfraw.iloc[-1]/self._dfraw.iloc[0]).values)/length
        dflist = [dict(asset = asset, returns = returns) for asset, returns in zip(self.get_assets(), returns)]
        df = pd.DataFrame(dflist)
        df = df.sort_values("returns", ascending=False)
        return df
    
    # def get_asset_metrics(self):
    #     asset_dict = {}
    #     for asset in self._dfraw.columns:
            
    
if __name__ == "__main__":
    # Example usage
    asset_list = ["AAPL", "MSFT", "GOOGL"]
    price_data = PriceData()
    print("Assets:", price_data.get_assets())
    print("Time period (years):", price_data.get_time_period())
    print("\nSummary Returns:")
    print(price_data.get_summary_returns())