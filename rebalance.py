import pandas as pd
from dataframe_loader import generate_df
from decimal import Decimal, ROUND_DOWN, getcontext

from hyperliquid.exchange import Exchange
from hyperliquid.info import Info

def percent_difference(val1, val2):
    avg = (val1 + val2) / 2
    return abs(val1 - val2) / avg

def round_to_sz_decimals(value: float, sz_decimals: int):
    getcontext().prec = 20
    quant = Decimal('1') / (Decimal('10') ** sz_decimals)
    return float(Decimal(value).quantize(quant, rounding=ROUND_DOWN))

def generate_target_allocations(account_value: float, clipped_weights, margin_mult: float):
  # Multiply weights to account val to get position sizes
  df = clipped_weights.copy()
  df['position_size'] = clipped_weights * account_value * margin_mult

  # convert to dict and return
  return df['position_size'].to_dict()

def generate_target_weights(top_coins: list[str], timeframe: str) -> pd.DataFrame | pd.Series:
  signal_coins = [] # List of (coin: str, inv_vol: float, is_long: bool)
  for coin in top_coins:
    df_coin = generate_df(coin, timeframe)
    if df_coin.empty:
      continue

    # Get current coin inv_vol and signal
    inv_vol = df_coin['inverse_volatility'].iloc[-1]
    signal = df_coin['signal'].iloc[-1]

    if signal == 1:
      signal_coins.append((coin, inv_vol, True))
    elif signal == -1:
      signal_coins.append((coin, inv_vol, False))

  # Get a df with all coins, their inverse volatility, and if they are long
  signal_coins_df = pd.DataFrame(signal_coins, columns=['coin', 'inv_vol', 'is_long'])
  signal_coins_df.set_index('coin', inplace=True)

  # Normalize inverse volatility weights and clip to 0.2
  total_inv_vol = signal_coins_df['inv_vol'].sum()
  signal_coins_df['normalized_weight'] = signal_coins_df['inv_vol'] / total_inv_vol
  signal_coins_df['clipped_weight'] = signal_coins_df['normalized_weight'].clip(upper=0.2)
  signal_coins_df.loc[~signal_coins_df['is_long'], 'clipped_weight'] *= -1

  return signal_coins_df[['clipped_weight']]

def close_position(exchange: Exchange, coin: str):
    print(f"Closing position in {coin}...")
    order_result = exchange.market_close(coin)
    if order_result["status"] == "ok":
        for status in order_result["response"]["data"]["statuses"]:
            try:
                filled = status["filled"]
                print(f'Order #{filled["oid"]} filled {filled["totalSz"]} @{filled["avgPx"]}')
            except KeyError:
                print(f'Error: {status["error"]}')

    return order_result

def open_position(info: Info, exchange: Exchange, coin: str, position_usd: float):
    is_buy = position_usd > 0
    position_usd = abs(position_usd)
    price = float(info.all_mids()[coin])
    universe = info.meta()['universe']
    sz_decimals = next(asset['szDecimals'] for asset in universe if asset['name'] == coin)
    target_size = round_to_sz_decimals(position_usd / price, sz_decimals)

    order_result = exchange.market_open(coin, is_buy, target_size)

    if order_result["status"] == "ok":
        for status in order_result["response"]["data"]["statuses"]:
            try:
                filled = status["filled"]
                print(f'Order #{filled["oid"]} filled {filled["totalSz"]} @{filled["avgPx"]}')
            except KeyError:
                print(f'Error: {status["error"]}')

    print(f"Opening {'Long' if is_buy else 'Short'} position in {coin}, target size: {target_size}")
    return order_result

def adjust_position(info: Info, exchange: Exchange, wallet_address: str, coin: str, new_position_usd: float, old_position_usd: float):

    if abs(new_position_usd - old_position_usd) < 10:
        print(f'Position size is less than 10, not sending {coin} order to market')
        return
    elif abs(percent_difference(new_position_usd, old_position_usd)) < 0.10:
        print(f'Position size change is less than 10%, not sending {coin} order to market ')
        return
    return open_position(info, exchange, coin, new_position_usd - old_position_usd)

def rebalance_portfolio(info: Info, exchange: Exchange, wallet_address: str, cur_positions: dict, target_positions: dict):
    cur_positions = cur_positions.copy()
    target_positions = target_positions.copy()

    # First, close all positions not in target positions and remove them from cur_positions
    only_in_cur_positions = set(cur_positions.keys()) - set(target_positions.keys())
    for coin in only_in_cur_positions:
        removed_suffix_coin = coin.removesuffix('-USD')
        close_position(exchange, coin)
        del cur_positions[coin]

    # Find all the coins that increase capital when the trade is executed (so that I can buy coins later),
    for coin, cur_position in list(cur_positions.items()):
        removed_suffix_coin = coin.removesuffix('-USD')
        target_position = target_positions.get(coin)
        if target_position is None:
            continue

        # Check if this is a reduction (not just smaller absolute value!)
        reducing_position = (
            (cur_position > 0 and target_position < cur_position) or
            (cur_position < 0 and target_position > cur_position)
        )

        # if they reduce capital, adjust them and remove them from cur and target positions
        if reducing_position:
            print('REDUCING POSITION:', coin)
            adjust_position(info, exchange, wallet_address, removed_suffix_coin, target_position, cur_position)
            del cur_positions[coin]
            del target_positions[coin]
            # capital_freed = abs(cur_position) - abs(target_position)
            # if abs(percent_difference(cur_position, target_position)) > 0.10 and capital_freed > 11:
            #     adjustments.append(coin)
    ####

    # Go through cur_positions again but this buy adjust the ones that will lower capital, then remove them
    for coin, cur_position in list(cur_positions.items()):
        removed_suffix_coin = coin.removesuffix('-USD')
        target_position = target_positions.get(coin)
        if target_position is None:
            continue
        adjust_position(info, exchange,  wallet_address, removed_suffix_coin, target_position, cur_position)
        del cur_positions[coin]
        del target_positions[coin]

    # Go through the rest of the target_weights that didn't have a position before and buy/sell them
    for coin, target_position in target_positions.items():
        removed_suffix_coin = coin.removesuffix('-USD')
        open_position(info, exchange, removed_suffix_coin, target_position)

    return
