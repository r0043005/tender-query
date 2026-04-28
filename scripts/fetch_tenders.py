#!/usr/bin/env python3
import sys
import os
import time
import json
import argparse
from datetime import datetime, timedelta
import urllib.parse

# 標準引入
try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    import requests
    HAS_CLOUDSCRAPER = False
    print("警告: 找不到 cloudscraper 模組，回退使用標準 requests。")

from bs4 import BeautifulSoup

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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://web.pcc.gov.tw/prkms/tender/common/basic/indexTenderBasic"
    }
    
    try:
        # 存取首頁
        print("存取首頁建立 Session...")
        scraper.get("https://web.pcc.gov.tw/prkms/tender/common/basic/indexTenderBasic", headers=headers, timeout=20)
        time.sleep(2)
        
        # 執行搜尋
        today = datetime.now()
        start_dt = today - timedelta(days=14)
        encoded_keyword = urllib.parse.quote(keyword)
        
        target_url = (
            f"https://web.pcc.gov.tw/prkms/tender/common/basic/readTenderBasic?"
            f"pageSize=50&firstSearch=true&searchType=basic&isBinding=N&isLogIn=N&level_1=on&"
            f"orgName=&orgId=&tenderName={encoded_keyword}&tenderId=&"
            f"tenderType=TENDER_DECLARATION&tenderWay=TENDER_WAY_ALL_DECLARATION&"
            f"dateType=isSpdt&tenderStartDate={start_dt.strftime('%Y/%m/%d')}&"
            f"tenderEndDate={today.strftime('%Y/%m/%d')}&"
            f"radProctrgCate=RAD_PROCTRG_CATE_3&policyAdvocacy="
        )
        
        print(f"發送搜尋請求...")
        response = scraper.get(target_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"錯誤: 狀態碼 {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.select_one("table.table_list") or soup.find("table", {"summary": "結果列表"})
        
        if not table:
            if "查無資料" in response.text:
                print("結果：查無符合條件的標案。")
            else:
                print(f"找不到表格。標題: {soup.title.string if soup.title else '無'}")
            return []
            
        rows = table.find_all("tr")[1:]
        tenders = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 7: continue
            try:
                org = cols[1].get_text(strip=True)
                name_cell = cols[2]
                name_text = name_cell.get_text(strip=True)
                
                # 案號通常在括號內
                job_no = ""
                if "(" in name_text and ")" in name_text:
                    job_no = name_text.split("(")[1].split(")")[0]
                
                tenders.append({
                    "job_no": job_no or name_text[:15],
                    "title": name_text,
                    "org": org,
                    "category": "勞務類",
                    "budget": cols[7].get_text(strip=True).replace(",", ""),
                    "publish": cols[5].get_text(strip=True).replace("/", ""),
                    "deadline": cols[6].get_text(strip=True),
                    "url": "https://web.pcc.gov.tw" + name_cell.find("a")["href"] if name_cell.find("a") else ""
                })
            except Exception: continue
                
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
    print(f"完成! 已儲存至 {args.output}")

if __name__ == "__main__":
    main()
