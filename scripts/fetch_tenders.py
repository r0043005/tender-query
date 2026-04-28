#!/usr/bin/env python3
"""
政府電子採購網標案資料抓取腳本 (爬蟲修正版)
依照使用者提供的成功搜尋參數進行抓取
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import time
from datetime import datetime, timedelta
import argparse

def fetch_tenders_by_scraping(keyword="清"):
    """
    直接從政府電子採購網爬取標案資訊 (使用 readTenderBasic 接口)
    """
    print(f"開始爬取關鍵字: {keyword}")
    
    # 使用使用者提供的成功網址接口
    url = "https://web.pcc.gov.tw/prkms/tender/common/basic/readTenderBasic"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://web.pcc.gov.tw/prkms/tender/common/basic/indexTenderBasic"
    }
    
    # 設定西元日期格式
    today = datetime.now()
    start_dt = today - timedelta(days=7) # 搜尋最近一週
    
    # 依照使用者提供的 URL 參數進行配置
    params = {
        "pageSize": "50",
        "firstSearch": "true",
        "searchType": "basic",
        "isBinding": "N",
        "isLogIn": "N",
        "level_1": "on",
        "tenderName": keyword,
        "tenderType": "TENDER_DECLARATION",
        "tenderWay": "TENDER_WAY_ALL_DECLARATION",
        "dateType": "isSpdt", # 等標期內
        "tenderStartDate": start_dt.strftime("%Y/%m/%d"),
        "tenderEndDate": today.strftime("%Y/%m/%d"),
        "radProctrgCate": "RAD_PROCTRG_CATE_3", # 勞務類
    }
    
    try:
        print(f"發送 GET 請求到 {url}...")
        print(f"參數: {params}")
        
        # 使用 GET 請求 (對應使用者提供的網址格式)
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"錯誤: 伺服器回傳狀態碼 {response.status_code}")
            if response.status_code == 403:
                print("偵測到 Cloudflare 阻擋。")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 尋找結果表格
        # 在 readTenderBasic 中，表格通常帶有 class="table_list"
        table = soup.select_one("table.table_list")
        if not table:
            table = soup.find("table", {"summary": "結果列表"})
        
        if not table:
            print("找不到結果表格，檢查是否查無資料。")
            if "查無資料" in response.text:
                print("網頁顯示：查無資料。")
            return []
            
        rows = table.find_all("tr")[1:] # 跳過標題列
        print(f"找到 {len(rows)} 筆原始資料")
        
        tenders = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 5:
                continue
            
            try:
                # 欄位解析 (依照 readTenderBasic 結構)
                # 1: 機關名稱, 2: 標案名稱/案號, 5: 公告日期, 6: 截止投標, 7: 預算金額
                org = cols[1].get_text(strip=True)
                
                name_cell = cols[2]
                name_text = name_cell.get_text(strip=True)
                
                job_no = ""
                name = name_text
                if "(" in name_text and ")" in name_text:
                    parts = name_text.split(")")
                    job_no = parts[0].replace("(", "").strip()
                    name = ")".join(parts[1:]).strip()
                
                # 公告日期
                publish_raw = cols[5].get_text(strip=True) # 可能是民國或西元，統一格式化
                publish = publish_raw.replace("/", "")
                
                # 截止日期
                deadline = cols[6].get_text(strip=True)
                
                # 預算金額
                budget_raw = cols[7].get_text(strip=True).replace(",", "")
                try:
                    budget = int(budget_raw)
                except:
                    budget = 0
                
                # URL
                link_tag = name_cell.find("a")
                tender_url = ""
                if link_tag and link_tag.get("href"):
                    href = link_tag.get("href")
                    if href.startswith("/"):
                        tender_url = f"https://web.pcc.gov.tw{href}"
                    else:
                        tender_url = href

                tenders.append({
                    "job_no": job_no or name_text[:15],
                    "title": name,
                    "org": org,
                    "category": "勞務類",
                    "budget": budget,
                    "publish": publish,
                    "deadline": deadline,
                    "url": tender_url
                })
            except Exception:
                continue
                
        return tenders

    except Exception as e:
        print(f"爬取過程發生錯誤: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description='政府電子採購網標案抓取 (readTenderBasic 版)')
    parser.add_argument('--keyword', '-k', default='清', help='搜尋關鍵字')
    parser.add_argument('--output', '-o', default='data/tenders.json', help='輸出路徑')
    args = parser.parse_args()
    
    tenders = fetch_tenders_by_scraping(args.keyword)
    
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(tenders, f, ensure_ascii=False, indent=2)
        
    print(f"完成! 已儲存 {len(tenders)} 筆標案到 {args.output}")

if __name__ == "__main__":
    main()
