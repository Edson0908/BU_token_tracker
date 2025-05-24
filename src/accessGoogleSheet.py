import gspread
from google.oauth2.service_account import Credentials

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

