from tkinter.constants import ARC
from hyperliquid.info import Info
import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
from dataframe_loader import generate_df
import account
from millify import millify
from rebalance import generate_target_weights, generate_target_allocations
from rebalance import rebalance_portfolio
from dotenv import load_dotenv
from data_fetcher import update_top_coins, hyperliquid_update_ohlcv
import os

load_dotenv()
WALLET_ADDRESS: str = os.getenv("WALLET_ADDRESS", "")
INITIAL_POSITION = 3500
ACCOUNT, EXCHANGE, INFO = account.get_account_data()
ACCOUNT_VALUE, POSITIONS = account.get_account_details(INFO)
MARGIN_MULTIPLIER = 1.2


st.set_page_config(
  page_title="Trend Following Dashboard",
  page_icon="🏂",
  layout="wide",
  initial_sidebar_state="expanded"
)
with open('./top_coins.json', "r") as f:
  top_coins: dict[str,int] = json.load(f)

def create_data_updaters():
  # Data candles
  if st.button("Update Data",
    on_click=hyperliquid_update_ohlcv,
    type='secondary',
    icon='🖊️',
    use_container_width=True
  ):
    st.success("✅ Updated candle data up to today!")

  # Top coins
  if st.button("Update Top 50 Coins by Volume (on Hyperliquid)",
    on_click=update_top_coins,
    args=(ACCOUNT, EXCHANGE, INFO),
    type='secondary',
    icon='🗓️',
    use_container_width=True
  ) :
    st.success("✅ Updated top 50 coins by volume! ")


with st.sidebar:
  st.title('🏂 Trend Following Dashboard')

  st.metric("Account Value", millify(ACCOUNT_VALUE, 2), delta=f'{millify((ACCOUNT_VALUE - INITIAL_POSITION) / INITIAL_POSITION * 100, 3)}%')

  coin_list = list(top_coins.keys())
  selected_coin = st.selectbox('Select a coin', coin_list)
  timeframe_list = ["1d"]
  selected_timeframe = st.selectbox('Select a timeframe', timeframe_list)
  window_size_list = [x for x in range(1, 365)]
  selected_window_size = st.select_slider('Select a window size', window_size_list, 21)

  create_data_updaters()

df = generate_df(selected_coin, selected_timeframe, 'csv').tail(selected_window_size)

def create_coin_chart():
  price_chart = go.Figure(
    data = [
      go.Candlestick(
        x=df.index,
        open=df['open'], high=df['high'],
        low=df['low'], close=df['close'],
        name="Price")
    ],
    layout = go.Layout(
      title=f"{selected_coin} Price",
      xaxis_rangeslider_visible=False
    )
  )

  # Price Chart Long & Short Signals
  buy_signals = df[df['signal'] == 1]
  sell_signals = df[df['signal'] == -1]
  price_chart.add_trace(go.Scatter(
    x=buy_signals.index,
    y=buy_signals['close'],
    mode='markers',
    marker=dict(size=20,
                color='MediumPurple',
                symbol='triangle-up',
                line=dict(
                    color='LightSkyBlue',
                    width=2
                )
            ),
    name='Buy Signal'
  ))

  price_chart.add_trace(go.Scatter(
      x=sell_signals.index,
      y=sell_signals['close'],
      mode='markers',
      marker=dict(size=20,
                  color='Orange',
                  symbol='triangle-down',
                  line=dict(
                      color='Black',
                      width=2
                  )
              ),
      name='Sell Signal'
  ))

  return price_chart

def create_view_positions(positions: dict):
  # build a DataFrame with coin, raw_value, abs_value, side

  pos_df = (
    pd.DataFrame.from_dict(positions, orient="index", columns=["raw_value"])
      .rename_axis("coin")
      .reset_index()
  )
  pos_df["abs_value"] = pos_df["raw_value"].abs()
  pos_df["side"] = pos_df["raw_value"].apply(lambda x: "Long" if x >= 0 else "Short")

  # configure columns
  st.dataframe(
    pos_df,
    column_order=("coin", "side", "abs_value"),
    column_config={
      "coin": st.column_config.TextColumn("Coin"),
      "side": st.column_config.TextColumn("Side"),
      "abs_value": st.column_config.ProgressColumn(
          "Position Size (USD)",
          format="dollar",
          min_value=0,
          max_value=pos_df["abs_value"].sum() * 0.2,
      ),
    },
    hide_index=True,
  )

def create_view_rebalancing_stats( target_weights: pd.DataFrame | pd.Series, position: dict[str, float]):
  target_coins = set(target_weights.index)
  cur_coins = set(position.keys())


  # Postions to add chart
  coins_to_add = list(target_coins - cur_coins)
  st.subheader("Positions to Add", divider='green')
  st.dataframe(coins_to_add)

  # Positions to remove chart
  coins_to_remove = list(cur_coins - target_coins)
  st.subheader("Positions to Remove", divider='red')
  st.dataframe(coins_to_remove)



# def create_positions
col = st.columns((3, 1), gap='medium')

with col[0]:
  st.markdown('#### Position Viewer')
  coin_chart = create_coin_chart()
  st.plotly_chart(coin_chart, use_container_width=True)
  ACCOUNT_VALUE, POSITIONS = account.get_account_details(INFO)
  create_view_positions(POSITIONS)

with col[1]:
  st.markdown('#### Rebalancing Zone')
  target_weights = generate_target_weights(list(top_coins.keys()), selected_timeframe)
  target_allocations = generate_target_allocations(ACCOUNT_VALUE, target_weights, MARGIN_MULTIPLIER)
  st.button("Rebalance Portfolio",
    on_click=rebalance_portfolio, args=(INFO, EXCHANGE, WALLET_ADDRESS, POSITIONS, target_allocations),
    type='secondary',
    icon='⚙️'
  )

  create_view_rebalancing_stats(target_weights, POSITIONS)
