import src.getTokenData as getTokenData
import src.accessGoogleSheet as accessGoogleSheet
import src.utils as utils
import os
import json
from dotenv import load_dotenv

load_dotenv(override=True)

def main():
    
    config = utils.load_config()

    headers, rows = accessGoogleSheet.get_sheet_data(config["google_config"]["api_key"], config["google_config"]["sheet_id"], config["google_config"]["sheet_name"])
    
    for row in rows:
        if row.get("Chain",None) in config["evm_chains"]:
            balance = getTokenData.get_evm_token_alance(row.get("Wallet Address",None), row.get("Token Address",None), row.get("Chain",None))
            row["Balance"] = balance
            
        else:
            balance = getTokenData.get_non_evm_token_balance(row.get("Wallet Address",None), row.get("Token Address",None), row.get("Chain",None))
            row["Balance"] = balance
        print(f"Token: {row.get('Symbol',None)} Balance: {balance}")
        prices = getTokenData.get_token_prices(row.get("TokenId"))
        print(json.dumps(prices, indent=4))
        current_price = prices.get("current_price") or 0
        one_day_ago_price = prices.get("one_day_ago_price") or 0
        seven_days_ago_price = prices.get("seven_days_ago_price") or 0
        thirty_days_ago_price = prices.get("thirty_days_ago_price") or 0
        row["Price"] = f"{current_price:.4f}"
        row["24h Change"] = f"{((current_price - one_day_ago_price) / one_day_ago_price * 100):.2f}%" if one_day_ago_price else "0.00%"
        row["7d Change"] = f"{((current_price - seven_days_ago_price) / seven_days_ago_price * 100):.2f}%" if seven_days_ago_price else "0.00%"
        row["30d Change"] = f"{((current_price - thirty_days_ago_price) / thirty_days_ago_price * 100):.2f}%" if thirty_days_ago_price else "0.00%"
        row["Value"] = f"{balance * current_price:.2f}"

    # 写回Google Sheet
    accessGoogleSheet.update_sheet_data(
        config["google_config"]["api_key"],
        config["google_config"]["sheet_id"],
        config["google_config"]["sheet_name"],
        headers,
        rows
    )
                                    
if __name__ == "__main__":
    main()