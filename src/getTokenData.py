import requests
import src.utils as utils
from dotenv import load_dotenv
import os
from web3 import Web3
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from solana.rpc.types import TokenAccountOpts
import subprocess
import json
from datetime import datetime, timedelta
import time

load_dotenv(override=True)
config = utils.load_config()

def get_evm_token_alance(walletAddress: str, tokenAddress: str, chain: str) -> float:
    """
    通过web3读取EVM链上ERC20余额。
    :param walletAddress: 钱包地址
    :param tokenAddress: 代币合约地址
    :param chainid: 链ID
    :param rpc_url: 链的RPC节点URL
    :return: 代币余额（已考虑decimals）
    """
    rpc_url = os.getenv(config["chains"][chain]["rpc_url"]) 
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print("Web3连接失败")
        return 0
    erc20_abi = [
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function",
        },
        {
            "constant": True,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "type": "function",
        },
    ]
    contract = w3.eth.contract(address=w3.to_checksum_address(tokenAddress), abi=erc20_abi)
    try:
        raw_balance = contract.functions.balanceOf(w3.to_checksum_address(walletAddress)).call()
        decimals = contract.functions.decimals().call()
        balance = raw_balance / (10 ** decimals)
        #print({"raw_balance": raw_balance, "decimals": decimals, "balance": balance})
        return balance
    except Exception as e:
        print(f"读取合约余额失败: {e}")
        return 0

def get_non_evm_token_balance(walletAddress: str, tokenAddress: str, chain: str) -> float:
    """
    通过API读取非EVM链上代币余额。
    :param walletAddress: 钱包地址
    :param tokenAddress: 代币合约地址
    :param chain: 链名
    :return: 代币余额（已考虑decimals）
    """ 
    if chain == "solana":
        return get_spl_token_balance(walletAddress, tokenAddress)
    elif chain == "dora":
        return get_dora_balance(walletAddress)
    elif chain == "aura":
        return get_aura_balance(walletAddress)
    elif chain in config["substrate_chains"]:
        return get_subscan_balance(walletAddress, chain)
    return 0


def get_spl_token_balance(walletAddress: str, tokenAddress: str) -> float:
    solana_rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    client = Client(solana_rpc_url)
    try:
        owner = Pubkey.from_string(walletAddress)
        mint = Pubkey.from_string(tokenAddress)
        opts = TokenAccountOpts(mint=mint)
        resp = client.get_token_accounts_by_owner(owner, opts)
        value = resp.value
        if not value:
            return 0
        token_account = value[0].pubkey
        balance_resp = client.get_token_account_balance(token_account)
        balance = float(balance_resp.value.ui_amount)
        return balance
    except Exception as e:
        print(f"Solana余额获取失败: {e}")
        return 0

def get_dora_balance(walletAddress: str) -> float:
    try:
        result = subprocess.run(
            [
                "dorad", "query", "bank", "balances", walletAddress,
                "--node", "https://vota-rpc.dorafactory.org:443",
                "--output", "json"
            ],
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        balances = data.get("balances", [])
        for balance in balances:
            if balance.get("denom") == "peaka":
                amount = int(balance.get("amount", "0"))
                dora_amount = amount / 1e18  # 转换为 DORA 单位
                return dora_amount
        return 0
    except subprocess.CalledProcessError as e:
        print("执行 dorad 命令时出错:", e)
        return 0

def get_aura_balance(walletAddress: str) -> float:
    url = f"https://lcd.aura.network/cosmos/bank/v1beta1/balances/{walletAddress}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        balances = data.get("balances", [])
        for balance in balances:
            if balance.get("denom") == "uaura":
                amount = int(balance.get("amount"))
                # 将 uaura 转换为 AURA（1 AURA = 1,000,000 uaura）
                return amount / 1_000_000
        return 0
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        return 0

def get_subscan_balance(walletAddress: str, chain: str) -> float:
    url = f"https://{chain}.api.subscan.io/api/scan/account/tokens"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    data = {
        "address": walletAddress,
        "row": 100,
        "page": 0
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        result = response.json()
        raw_balance = int(result.get("data").get("native")[0].get("balance"))
        decimals = result.get("data").get("native")[0].get("decimals")
        balance = raw_balance / 10**decimals
        return balance
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        return 0

def get_token_prices(token_id):
    one_day_ago_date = (datetime.now() - timedelta(days=1)).strftime("%d-%m-%Y")
    seven_days_ago_date = (datetime.now() - timedelta(days=7)).strftime("%d-%m-%Y")
    thirty_days_ago_date = (datetime.now() - timedelta(days=30)).strftime("%d-%m-%Y")
    current_price = get_token_price_by_date(token_id, None)
    time.sleep(config["params"]["sleep_time"])
    one_day_ago_price = get_token_price_by_date(token_id, one_day_ago_date)
    time.sleep(config["params"]["sleep_time"])
    seven_days_ago_price = get_token_price_by_date(token_id, seven_days_ago_date)
    time.sleep(config["params"]["sleep_time"])
    thirty_days_ago_price = get_token_price_by_date(token_id, thirty_days_ago_date)
    time.sleep(config["params"]["sleep_time"])
    return {
        "current_price": current_price,
        "one_day_ago_price": one_day_ago_price,
        "seven_days_ago_price": seven_days_ago_price,
        "thirty_days_ago_price": thirty_days_ago_price
    }

def get_token_price_by_date(token_id, date=None):
    max_retries = config["params"]["max_retries"]
    try_count = 0
    url = "https://api.coingecko.com/api/v3/simple/price"
    headers = {
        "Accept": "application/json",
        "X-CoinGecko-Api-Key": os.getenv("COINGECKO_API_KEY")  
    }
    while try_count < max_retries:
        try:
            if date:
                # Check if the date is within the last 365 days
                today = datetime.now()
                date_obj = datetime.strptime(date, "%d-%m-%Y")
                if (today - date_obj).days > 365:
                    print(f"Date {date} is outside the allowed range.")
                    return None
                # 获取指定日期的价格
                historical_url = f"https://api.coingecko.com/api/v3/coins/{token_id}/history?date={date}&localization=false"
                response = requests.get(historical_url, headers=headers)
                response.raise_for_status()
                data = response.json()
                if 'market_data' in data and 'current_price' in data['market_data']:
                    price = data['market_data']['current_price']['usd']
                else:
                    print(f"No historical data available for {token_id} on {date}.")
                    return None
                return price
            else:
                # 获取当前价格
                params = {
                    "ids": token_id,
                    "vs_currencies": "usd"
                }
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                price = data[token_id]["usd"]
                return price
        except requests.RequestException as e:
            try_count += 1
            print(f"获取{token_id}价格时发生错误: {e}，重试({try_count}/{max_retries})...")
            time.sleep(config["params"]["sleep_time"])
            if try_count >= max_retries:
                print(f"已达到最大重试次数({max_retries})，放弃。")
                return None