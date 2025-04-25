from hyperliquid.info import Info
from hyperliquid.utils import constants
from hyperliquid.exchange import Exchange
import eth_account
from eth_account.signers.local import LocalAccount
from dotenv import load_dotenv
import os

def get_account_data() -> tuple[LocalAccount, Exchange, Info]:
  load_dotenv()
  account_adr = os.getenv("WALLET_ADDRESS")
  agent_key = os.getenv("API_PRIVATE_KEY")
  account: LocalAccount = eth_account.Account.from_key(agent_key)
  print("Running with agent address:", account.address)
  exchange = Exchange(account, constants.MAINNET_API_URL, account_address=account_adr)
  info = Info(constants.MAINNET_API_URL)

  return account, exchange, info

def get_account_details(info: Info) -> tuple[float, dict[str, float]]:
  load_dotenv()
  wallet_adr: str = os.getenv("WALLET_ADDRESS", "")
  user_state = info.user_state(wallet_adr)

  # Extract desired values
  account_value = user_state["marginSummary"]["accountValue"]
  coin_and_position = {}
  for asset_info in user_state["assetPositions"]:
    pos = asset_info.get("position", {})
    coin = pos.get("coin")
    position_usdt = float(pos.get("positionValue"))
    if float(pos.get("szi")) < 0:
      position_usdt *= -1
    if coin and position_usdt:
      coin_and_position[coin] = position_usdt
  sorted_coin_and_position = {k: coin_and_position[k] for k in sorted(coin_and_position)}
  account_positions = sorted_coin_and_position
  return float(account_value), account_positions
