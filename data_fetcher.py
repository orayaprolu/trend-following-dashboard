import json
from typing import Optional
import time
import os
import csv
import pandas as pd
from datetime import datetime

from eth_account.signers.local import LocalAccount
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.ccxt import hyperliquid as HyperliquidSync

def update_top_coins(account: LocalAccount, exchange: Exchange, info: Info):
  # fetch meta + contexts
  meta, ctxs = info.meta_and_asset_ctxs()

  # Zip them together safely
  volume_data = []
  for meta_item, ctx in zip(meta["universe"], ctxs):
      coin = meta_item["name"]
      volume = float(ctx.get("dayNtlVlm", 0))
      volume_data.append((coin, volume))

  # Sort and take top 50
  top_50 = sorted(volume_data, key=lambda x: x[1], reverse=True)[:50]

  # build name→perpetual-ID map
  perp_id_map = {
    meta_item["name"]: idx
    for idx, meta_item in enumerate(meta["universe"])
  }

  # assume `top_50` is your list of [(coin, volume),…]
  top_50_names = [coin for coin, _ in top_50]

  # filter down to just the top-50 coins
  top50_perp_ids = { coin: perp_id_map[coin] for coin in top_50_names }

  with open("top_coins.json", "w") as f:
    json.dump(top50_perp_ids, f, indent=2)

def hyperliquid_update_ohlcv(timeframe: str = '1d', limit: int = 1000):

  # Initialize exchange
  exchange = HyperliquidSync()
  exchange.load_markets()

  def update_csv(asset_id: str, asset_name: str):
    csv_filename = f'csv/{asset_name}_{timeframe}.csv'

    last_updated = 0
    if os.path.exists(csv_filename):
      df = pd.read_csv(csv_filename)
      last_date = df["date"].iat[-1]
      ts = pd.to_datetime(last_date, utc=True)
      ms = int(ts.timestamp() * 1_000)             # seconds → milliseconds
      last_updated = ms
    else:
      # create parent dir if needed
      os.makedirs(os.path.dirname(csv_filename), exist_ok=True)
      # empty DataFrame with the right columns
      df = pd.DataFrame(columns=["date","open","high","low","close","volume"])
      # write it out (this creates the file with just a header)
      df.to_csv(csv_filename, index=False)


    ohlcv = exchange.fetch_ohlcv(asset_id, timeframe, since=last_updated, limit=limit)
    if not ohlcv:
      print(f'No new data for {asset_name}')

    # Prepare updated rows (replacing recent ones)
    new_rows_dict = {}
    for candle in ohlcv:
        timestamp, o, h, l, c, v = candle
        date_str = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d')
        new_rows_dict[date_str] = [date_str, round(o, 6), round(h, 6), round(l, 6), round(c, 6), round(v, 6)]

    updated_rows = []
    if os.path.exists(csv_filename):
        with open(csv_filename, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            for row in reader:
                if row[0] not in new_rows_dict:
                    updated_rows.append(row)
    else:
        header = ["date", "open", "high", "low", "close", "volume"]

    # Append/replace recent rows
    updated_rows.extend(new_rows_dict[date] for date in sorted(new_rows_dict))

    # Write to file
    with open(csv_filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in updated_rows:
            writer.writerow(row)

    print(f"Updated {csv_filename} with {len(new_rows_dict)} recent rows.")

  # Load your JSON with assets
  with open("top_coins.json", "r") as f:
    top_coins: dict[str,int]  = json.load(f)

  for coin, asset_id in top_coins.items():
    update_csv(str(asset_id), coin)


###### TESTING OR MANUALLY RUNNING FILE

# from account import get_account_data
# account, exchange, info = get_account_data()
# update_top_coins(account, exchange, info)
# hyperliquid_update_ohlcv()
