import pandas as pd
import numpy as np

def create_volatility_metrics(df: pd.DataFrame):
    df = df.copy()
    df['volatility'] = df['close'].pct_change().rolling(20).std() * np.sqrt(365)
    df['inverse_volatility'] = 1 / df['volatility']

    return df
