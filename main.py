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

        row["Price"] = current_price
        row["24h Change"] = (current_price - one_day_ago_price) / one_day_ago_price if one_day_ago_price else 0
        row["7d Change"] = (current_price - seven_days_ago_price) / seven_days_ago_price if seven_days_ago_price else 0
        row["30d Change"] = (current_price - thirty_days_ago_price) / thirty_days_ago_price if thirty_days_ago_price else 0
        row["Value"] = balance * current_price

    # 写回Google Sheet
    accessGoogleSheet.update_sheet_data(
        config["google_config"]["api_key"],
        config["google_config"]["sheet_id"],
        config["google_config"]["sheet_name"],
        headers,
        rows
    )
    print("写入Google Sheet成功")
    # 设置Google Sheet的列格式
    accessGoogleSheet.set_sheet_format(
        config["google_config"]["api_key"],
        config["google_config"]["sheet_id_num"],
        config["google_config"]["sheet_name"],
        headers
    )
    print("设置Google Sheet格式成功")
                                    
if __name__ == "__main__":
    main()