#!/usr/bin/env python3
"""
政府電子採購網標案資料抓取腳本
抓取含有指定關鍵字的勞務採購標案

使用方法:
    python fetch_tenders.py
    python fetch_tenders.py --keyword 清
    python fetch_tenders.py --output ./data/tenders.json
"""

import requests
import json
import sys
import argparse
from datetime import datetime, timedelta

# API 端點
API_SOURCES = [
    # pcc.mlwmlw.org API
    {
        "name": "pcc.mlwmlw.org",
        "base_url": "https://pcc.mlwmlw.org/api",
        "endpoint": "/keyword/{keyword}",
        "method": "GET"
    },
    # 政府開放資料平台 - 行政院公共工程委員會
    {
        "name": "data.gov.tw - 工程會",
        "base_url": "https://web.pcc.gov.tw",
        "endpoint": "/pis/prkms/tender/common/basic/indexTenderBasic",
        "method": "GET"
    }
]

def fetch_from_mlwmlw(keyword):
    """從 pcc.mlwmlw.org 抓取標案資料"""
    url = f"https://pcc.mlwmlw.org/api/keyword/{keyword}"
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (compatible; TenderQueryBot/1.0)'
    }

    try:
        print(f"嘗試從 {url} 抓取資料...")
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if 'json' in content_type:
                data = response.json()
                if data and len(data) > 0:
                    print(f"成功從 pcc.mlwmlw.org 抓取 {len(data)} 筆資料")
                    return data
                else:
                    print("pcc.mlwmlw.org 回傳空資料")
            else:
                print(f"pcc.mlwmlw.org 回傳非 JSON 格式: {content_type}")
        else:
            print(f"pcc.mlwmlw.org 回應狀態碼: {response.status_code}")
    except Exception as e:
        print(f"pcc.mlwmlw.org 抓取失敗: {e}")

    return None

def fetch_from_government_pcc():
    """從政府電子採購網直接抓取（需要處理登入和驗證）"""
    # 政府電子採購網需要登入才能查詢，這邊提供查詢網址
    # 使用者可以透過瀏覽器登入後手動匯出 CSV

    print("政府電子採購網需要登入驗證，無法直接自動抓取")
    print("建議手動操作:")
    print("1. 前往 https://web.pcc.gov.tw/prkms/tender/common/basic/indexTenderBasic")
    print("2. 登入後搜尋關鍵字")
    print("3. 點擊「匯出 Excel」下載資料")

    return None

def fetch_from_data_gov_taiwan():
    """從政府資料開放平台抓取採購資料"""
    # 搜尋政府資料開放平台的採購相關資料集
    search_url = "https://data.gov.tw/api/v2/rest/dataset/search"
    params = {
        'q': '採購 標案',
        'limit': 10
    }

    try:
        print("搜尋政府資料開放平台的採購相關資料集...")
        response = requests.get(search_url, params=params, timeout=30)

        if response.status_code == 200:
            data = response.json()
            datasets = data.get('datasets', [])
            print(f"找到 {len(datasets)} 個相關資料集")

            for ds in datasets[:5]:
                print(f"  - {ds.get('name', '未命名')}: {ds.get('resource_url', '無連結')}")
    except Exception as e:
        print(f"政府資料開放平台搜尋失敗: {e}")

def process_tenders(data, keyword):
    """處理和過濾標案資料"""
    if not data:
        return []

    tenders = []

    for record in data:
        tender = {
            "id": record.get("job_no") or record.get("id") or "",
            "name": record.get("title") or record.get("name") or "",
            "organization": record.get("org") or record.get("unit") or record.get("agency") or "",
            "type": "labor",  # 預設為勞務採購
            "budget": 0,
            "publishDate": "",
            "deadline": "",
            "daysLeft": 0,
            "pk": record.get("pk") or record.get("id") or ""
        }

        # 處理預算
        if record.get("budget"):
            budget_str = str(record["budget"])
            budget_str = budget_str.replace(",", "").replace("$", "").replace("元", "")
            try:
                tender["budget"] = int(budget_str)
            except:
                pass

        # 處理日期
        if record.get("publish"):
            tender["publishDate"] = record["publish"]
        if record.get("deadline") or record.get("end_date"):
            tender["deadline"] = record.get("deadline") or record.get("end_date")

        tenders.append(tender)

    return tenders

def save_tenders(tenders, output_path):
    """儲存標案資料到 JSON 檔案"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(tenders, f, ensure_ascii=False, indent=2)
    print(f"已儲存 {len(tenders)} 筆資料到 {output_path}")

def main():
    parser = argparse.ArgumentParser(description='抓取政府電子採購網標案資料')
    parser.add_argument('--keyword', '-k', default='清', help='搜尋關鍵字 (預設: 清)')
    parser.add_argument('--output', '-o', default='./data/tenders.json', help='輸出檔案路徑')
    parser.add_argument('--test', action='store_true', help='僅測試 API 連線')

    args = parser.parse_args()

    print("=" * 50)
    print("政府電子採購網標案資料抓取工具")
    print(f"關鍵字: {args.keyword}")
    print("=" * 50)

    if args.test:
        # 僅測試 API 連線
        print("\n[測試模式] 測試各 API 來源的可用性...")

        result = fetch_from_mlwmlw(args.keyword)
        if result:
            print("✓ pcc.mlwmlw.org API 可用")
        else:
            print("✗ pcc.mlwmlw.org API 不可用")

        fetch_from_government_pcc()
        fetch_from_data_gov_taiwan()

        return

    # 嘗試從各來源抓取資料
    print(f"\n嘗試抓取含「{args.keyword}」關鍵字的標案資料...\n")

    tenders = None

    # 嘗試 pcc.mlwmlw.org
    raw_data = fetch_from_mlwmlw(args.keyword)
    if raw_data:
        tenders = process_tenders(raw_data, args.keyword)

    # 如果都抓不到，回傳空陣列
    if not tenders or len(tenders) == 0:
        print("\n警告: 所有 API 都無法取得資料，將建立空白資料檔案")
        tenders = []

    # 確保輸出目錄存在
    import os
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 儲存結果
    save_tenders(tenders, args.output)

    print("\n" + "=" * 50)
    print("抓取完成")
    print("=" * 50)

if __name__ == "__main__":
    main()
