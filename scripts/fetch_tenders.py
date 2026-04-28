#!/usr/bin/env python3
"""
政府電子採購網標案資料抓取腳本 (爬蟲版)
直接從 web.pcc.gov.tw 抓取資料
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import time
from datetime import datetime, timedelta
import argparse

def to_minguo_date(date_obj):
    """將 datetime 物件轉換為民國年格式 (YYY/MM/DD)"""
    return f"{date_obj.year - 1911}/{date_obj.month:02d}/{date_obj.day:02d}"

def fetch_tenders_by_scraping(keyword="清"):
    """
    直接從政府電子採購網爬取標案資訊
    """
    print(f"開始爬取關鍵字: {keyword}")
    
    # 搜尋網址 (招標公告查詢)
    url = "https://web.pcc.gov.tw/prkms/tender/common/noticeAll/readNoticeAll"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://web.pcc.gov.tw/prkms/tender/common/noticeAll/indexNoticeAll",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    # 設定搜尋日期範圍 (公告日期：今天到過去 30 天)
    today = datetime.now()
    start_dt = today - timedelta(days=30)
    
    # 參數設定說明：
    # tenderStatus: '4' 為「等標期內」
    # tenderType: '1' 為「招標公告」
    # radProctrgCate: '3' 為「勞務類」
    payload = {
        "method": "readNoticeAll",
        "isSearch": "true",
        "tenderName": keyword,
        "tenderStatus": "4", # 僅選取「等標期內」
        "tenderType": "1", # 招標公告
        "radProctrgCate": "3", # 勞務類
        "tenderDateStart": to_minguo_date(start_dt),
        "tenderDateEnd": to_minguo_date(today),
        "pageSize": "100",
        "firstPage": "true"
    }
    
    try:
        print(f"發送 POST 請求到 {url}...")
        print(f"篩選條件: 等標期內, 勞務類, 公告日期 {to_minguo_date(start_dt)} ~ {to_minguo_date(today)}")
        
        response = requests.post(url, data=payload, headers=headers, timeout=30)
        
        if response.status_code == 403:
            print("錯誤: 403 Forbidden. 可能是被 Cloudflare 阻擋了。")
            import sys
            sys.exit(1)
            
        if response.status_code != 200:
            print(f"錯誤: 伺服器回傳狀態碼 {response.status_code}")
            import sys
            sys.exit(1)
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 尋找結果表格
        table = soup.select_one("table.table_list")
        if not table:
            table = soup.find("table", {"summary": "結果列表"})
        if not table:
            table = soup.find("table", {"id": "item"})

        if not table:
            if "查無資料" in response.text:
                print("網頁顯示：查無資料 (等標期內目前可能沒有含「清」字的勞務標案)")
            else:
                print("找不到結果表格，網頁結構可能已改變。")
            return []
            
        rows = table.find_all("tr")[1:] # 跳過標題列
        print(f"找到 {len(rows)} 筆原始資料")
        
        tenders = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 5:
                continue
            
            try:
                # 欄位解析
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
                publish_raw = cols[5].get_text(strip=True)
                p_parts = publish_raw.split("/")
                if len(p_parts) == 3:
                    publish = f"{int(p_parts[0])+1911}{p_parts[1]}{p_parts[2]}"
                else:
                    publish = publish_raw
                    
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
    parser = argparse.ArgumentParser(description='政府電子採購網標案抓取 (等標期內版)')
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
