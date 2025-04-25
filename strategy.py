import pandas as pd
# import numpy as np
from utils.indicators import twenty_day_high_within_lookback, twenty_day_low_within_lookback

# Must return a df with a col called signal in my framework !!
def loose_pants_trend(df: pd.DataFrame, lookback: int = 5) -> pd.DataFrame:
    """
    Strategy: Enter position when close is highest in `lookback` period.
    Must return a DataFrame with a 'signal' column.
    """

    df = df.copy()

    # Compute 20 day high signals
    long_signal = twenty_day_high_within_lookback(df, lookback)
    short_signal = twenty_day_low_within_lookback(df, lookback)
    df['signal'] = (long_signal + short_signal).shift(1)

    return df



    # # Step 3: Compute log returns and EW volatility
    # df['log_return'] = np.log(df['close'] / df['close'].shift(1))
    # df['recent_volatility'] = df['log_return'].ewm(span=recent_sd_daily_returns, adjust=False).std()

    # # Step 4: Volatility-standardize
    # df['volatility_standardized_forecast'] = df['raw_forecast'] / df['recent_volatility']

    # # Step 5: Forecast scalar to target E[|x|] = 10
    # forecast_scalar = 10 / df['volatility_standardized_forecast'].abs().mean()
    # df['volatility_standardized_forecast'] *= forecast_scalar

    # # # Step 6: Clip extreme values
    # df['volatility_standardized_forecast'] = np.clip(df['volatility_standardized_forecast'], -20, 20)
