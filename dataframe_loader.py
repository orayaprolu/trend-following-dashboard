import os
import pandas as pd

from volatility_metrics import create_volatility_metrics
from strategy import loose_pants_trend

def generate_df(symbol: str, timeframe: str, base_path='csv'):
  filename = f"{symbol}_{timeframe}.csv"
  filepath = os.path.join(base_path, filename)
  if not os.path.exists(filepath):
    raise FileNotFoundError(f"File {filepath} not found.")
  df = pd.read_csv(filepath)
  df.set_index('date', inplace=True)
  df = df.sort_index()
  df = create_volatility_metrics(df) # Create risk metrics
  df = loose_pants_trend(df) # Apply strategy

  return df
