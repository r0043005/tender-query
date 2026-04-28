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
from datetime import datetime
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
        "Referer": "https://web.pcc.gov.tw/prkms/tender/common/noticeAll/indexNoticeAll"
    }
    
    # 設定搜尋日期範圍 (今天到過去 30 天)
    today = datetime.now()
    # startDate = to_minguo_date(today) # 只抓今天的? 不，通常抓最近一段時間的
    # 根據需求，通常是抓取「等標期內」的標案，所以我們搜尋最近一個月公告的
    import datetime as dt
    start_dt = today - dt.timedelta(days=30)
    
    payload = {
        "method": "query",
        "searchQue": "true",
        "tenderName": keyword,
        "tenderStatus": "4,5,21,29", # 招標中、等標期內
        "tenderType": "TENDER_DECLARATION", # 招標公告
        "radProctrgCate": "3", # 勞務類
        "startDate": to_minguo_date(start_dt),
        "endDate": to_minguo_date(today),
        "pageSize": "100"
    }
    
    try:
        print(f"發送 POST 請求到 {url}...")
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
        # 根據 web.pcc.gov.tw 的結構，結果通常在 class 為 table_list 的表格中
        table = soup.select_one("table.table_list")
        if not table:
            # 嘗試另外一種可能的選擇器
            table = soup.find("table", {"summary": "結果列表"})
            
        if not table:
            print("找不到結果表格，可能是沒有符合條件的標案或頁面結構已改變")
            # 打印部分 HTML 供偵錯
            # print(response.text[:1000])
            return []
            
        rows = table.find_all("tr")[1:] # 跳過標題列
        print(f"找到 {len(rows)} 筆原始資料")
        
        tenders = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 5:
                continue
                
            # 欄位解析 (這部分需要根據實際頁面結構調整)
            # 0: 序號, 1: 機關名稱, 2: 標案案號/名稱, 3: 傳輸次數, 4: 招標方式, 5: 公告日期, 6: 截止投標, 7: 預算金額
            
            try:
                org = cols[1].get_text(strip=True)
                
                # 標案名稱和案號通常在同一個單元格，案號在括號內或有換行
                name_cell = cols[2]
                name_text = name_cell.get_text(strip=True)
                
                # 試著拆分案號和名稱
                # 案號通常在前面
                job_no = ""
                name = name_text
                if "(" in name_text and ")" in name_text:
                    job_no = name_text.split("(")[1].split(")")[0]
                    name = name_text.split(")")[1].strip() if ")" in name_text else name_text
                elif "\n" in name_cell.get_text():
                    parts = [p.strip() for p in name_cell.get_text().split("\n") if p.strip()]
                    if len(parts) >= 2:
                        job_no = parts[0]
                        name = parts[1]
                
                # 公告日期 (民國年)
                publish_raw = cols[5].get_text(strip=True) # 113/04/28
                # 轉換為 YYYYMMDD
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
                
                # 詳情 URL
                link_tag = name_cell.find("a")
                tender_url = ""
                if link_tag and link_tag.get("href"):
                    href = link_tag.get("href")
                    if href.startswith("/"):
                        tender_url = f"https://web.pcc.gov.tw{href}"
                    else:
                        tender_url = href

                tenders.append({
                    "job_no": job_no or name_text[:15], # 如果沒抓到案號，暫用前15字
                    "title": name,
                    "org": org,
                    "category": "勞務類",
                    "budget": budget,
                    "publish": publish,
                    "deadline": deadline,
                    "url": tender_url
                })
            except Exception as e:
                print(f"解析列時發生錯誤: {e}")
                continue
                
        return tenders

    except Exception as e:
        print(f"爬取過程發生錯誤: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description='政府電子採購網標案抓取 (爬蟲版)')
    parser.add_argument('--keyword', '-k', default='清', help='搜尋關鍵字')
    parser.add_argument('--output', '-o', default='data/tenders.json', help='輸出路徑')
    args = parser.parse_args()
    
    tenders = fetch_tenders_by_scraping(args.keyword)
    
    if not tenders:
        print("警告: 未抓取到任何資料")
        # 如果爬蟲失敗，可以考慮回退到 API 
        # 但這裡我們依照使用者要求，只實作爬蟲邏輯
    
    # 確保目錄存在
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(tenders, f, ensure_ascii=False, indent=2)
        
    print(f"完成! 已儲存 {len(tenders)} 筆標案到 {args.output}")

if __name__ == "__main__":
    main()
