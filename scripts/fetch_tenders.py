#!/usr/bin/env python3
"""
政府電子採購網標案資料抓取腳本 (Cloudscraper 強化版)
使用 cloudscraper 繞過 Cloudflare 防護
"""

try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    import requests
    HAS_CLOUDSCRAPER = False
    print("警告: 找不到 cloudscraper 模組，將回退使用標準 requests。")

from bs4 import BeautifulSoup
import json
import os
import time
from datetime import datetime, timedelta
import argparse

def fetch_tenders_by_scraping(keyword="清"):
    print(f"開始爬取關鍵字: {keyword}")
    
    # 建立爬取實例
    if HAS_CLOUDSCRAPER:
        print("使用 cloudscraper 進行爬取...")
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
    else:
        print("使用標準 requests 進行爬取...")
        scraper = requests.Session()
    
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://web.pcc.gov.tw/prkms/tender/common/basic/indexTenderBasic"
    }
    
    try:
        url = "https://web.pcc.gov.tw/prkms/tender/common/basic/readTenderBasic"
        
        today = datetime.now()
        start_dt = today - timedelta(days=7) # 跟隨使用者成功的參數範例 (約一週)
        
        # 完整對齊使用者手動搜尋成功的參數
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
            "policyAdvocacy": ""
        }
        
        print(f"發送搜尋請求 (Cloudscraper) 到 {url}...")
        response = scraper.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"錯誤: 狀態碼 {response.status_code}")
            # 輸出部分內容診斷
            print(f"DEBUG Content: {response.text[:200]}")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 尋找結果表格 (readTenderBasic 的結構)
        table = soup.select_one("table.table_list")
        if not table:
            table = soup.find("table", {"summary": "結果列表"})
        
        if not table:
            if "查無資料" in response.text:
                print("結果：網頁顯示「查無資料」，請確認該日期區間是否有標案。")
            else:
                print("警告：仍然找不到表格結構，可能需要手動確認 HTML 內容。")
                print(f"Page Title: {soup.title.string if soup.title else 'No Title'}")
                # 輸出 HTML 前 500 字元以便在 Actions 日誌中查看
                print(f"HTML Snippet: {response.text[:500]}")
            return []
            
        rows = table.find_all("tr")
        tenders = []
        
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 7:
                continue
            
            try:
                # 欄位：1:機關, 2:名稱(案號), 5:公告日, 6:截止日, 7:預算
                org = cols[1].get_text(strip=True)
                name_cell = cols[2]
                name_text = name_cell.get_text(strip=True)
                
                # 案號處理
                job_no = ""
                name = name_text
                if "(" in name_text and ")" in name_text:
                    parts = name_text.split(")")
                    job_no = parts[0].replace("(", "").strip()
                    name = ")".join(parts[1:]).strip()
                
                # 公告日期
                publish = cols[5].get_text(strip=True).replace("/", "")
                
                # 預算
                budget_raw = cols[7].get_text(strip=True).replace(",", "")
                budget = int(budget_raw) if budget_raw.isdigit() else 0

                tenders.append({
                    "job_no": job_no or name_text[:15],
                    "title": name,
                    "org": org,
                    "category": "勞務類",
                    "budget": budget,
                    "publish": publish,
                    "deadline": cols[6].get_text(strip=True),
                    "url": "https://web.pcc.gov.tw" + name_cell.find("a")["href"] if name_cell.find("a") else ""
                })
            except Exception:
                continue
                
        print(f"解析成功，抓取到 {len(tenders)} 筆標案。")
        return tenders

    except Exception as e:
        print(f"爬取錯誤: {e}")
        return []

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--keyword', '-k', default='清')
    parser.add_argument('--output', '-o', default='data/tenders.json')
    args = parser.parse_args()
    
    tenders = fetch_tenders_by_scraping(args.keyword)
    
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(tenders, f, ensure_ascii=False, indent=2)
    print(f"已更新 {args.output}")

if __name__ == "__main__":
    main()
