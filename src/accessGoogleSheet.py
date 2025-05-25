import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import src.utils as utils

def get_client(key):
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_file(
        key, 
        scopes=scope
    )
    return gspread.authorize(creds)

def get_sheet_data(api_key, sheet_id, sheet_name):
    # 打开Google Sheet
    client = get_client(api_key)
    spreadsheet = client.open(sheet_id)
    sheet = spreadsheet.worksheet(sheet_name)

    # 获取所有数据，包括表头
    headers = sheet.row_values(1)
    raw_data = sheet.get_all_records()
    
    return headers, raw_data

def get_row_by_criteria(api_key, sheet_id, sheet_name, key, value):
    
    client = get_client(api_key)
    spreadsheet = client.open(sheet_id)
    sheet = spreadsheet.worksheet(sheet_name)

    raw_data = sheet.get_all_records()
    matching_rows = [row for row in raw_data if row.get(key) == value]
    
    return matching_rows

def update_sheet_data(api_key, sheet_id, sheet_name, headers, rows):
    """
    将rows（list of dict）写回Google Sheet，覆盖原有内容。
    :param api_key: Google API密钥文件路径
    :param sheet_id: 表格ID
    :param sheet_name: 工作表名
    :param headers: 表头list
    :param rows: list of dict，每个dict为一行
    """
    client = get_client(api_key)
    spreadsheet = client.open(sheet_id)
    sheet = spreadsheet.worksheet(sheet_name)

    # 组装数据，第一行为headers，后面为每行数据
    data = [headers]
    for row in rows:
        data.append([row.get(h, "") for h in headers])
    # 清空原有内容
    sheet.clear()
    # 批量写入
    sheet.update('A1', data)

def set_sheet_format(api_key, sheet_id, sheet_name, headers):
    """
    根据config和表头设置Google Sheet的列格式。
    :param api_key: Google API密钥文件路径
    :param sheet_id: 表格ID
    :param sheet_name: 工作表名
    :param headers: 表头list
    :param config: 配置dict，指定每列格式
    """
    format_config = utils.load_config()["sheet_format"][sheet_name]
    # 获取sheetId
    gc = get_client(api_key)
    spreadsheet = gc.open_by_key(sheet_id)
    worksheet = spreadsheet.worksheet(sheet_name)
    sheet_id_num = worksheet._properties['sheetId']

    # 列名到列号的映射
    col_map = {h: i for i, h in enumerate(headers)}
    requests = []
    for col, fmt in format_config.items():
        if col not in col_map:
            continue
        col_idx = col_map[col]
        if fmt == 'number_2':
            number_format = {"type": "NUMBER", "pattern": "0.00"}
        elif fmt == 'number_4':
            number_format = {"type": "NUMBER", "pattern": "0.0000"}
        elif fmt == 'percent_2':
            number_format = {"type": "PERCENT", "pattern": "0.00%"}
        else:
            continue
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id_num,
                    "startRowIndex": 1,  # 跳过表头
                    "startColumnIndex": col_idx,
                    "endColumnIndex": col_idx + 1
                },
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": number_format
                    }
                },
                "fields": "userEnteredFormat.numberFormat"
            }
        })
    # 用googleapiclient发请求
    creds = Credentials.from_service_account_file(api_key, scopes=[
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ])
    service = build('sheets', 'v4', credentials=creds)
    body = {"requests": requests}
    service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body=body).execute()

