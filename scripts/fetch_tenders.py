#!/usr/bin/env python3
import sys
import os
import time
import json
import argparse
from datetime import datetime, timedelta
import urllib.parse

try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    import requests
    HAS_CLOUDSCRAPER = False

from bs4 import BeautifulSoup

def fetch_tenders_by_scraping(keyword="清"):
    print(f"Keyword: {keyword}")
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}) if HAS_CLOUDSCRAPER else requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://web.pcc.gov.tw/prkms/tender/common/basic/indexTenderBasic"
    }
    
    try:
        # Get Session
        scraper.get("https://web.pcc.gov.tw/prkms/tender/common/basic/indexTenderBasic", headers=headers, timeout=20)
        time.sleep(2)
        
        # Search URL
        today = datetime.now()
        start_dt = today - timedelta(days=14)
        encoded_keyword = urllib.parse.quote(keyword)
        
        url = (
            f"https://web.pcc.gov.tw/prkms/tender/common/basic/readTenderBasic?"
            f"pageSize=50&firstSearch=true&searchType=basic&isBinding=N&isLogIn=N&level_1=on&"
            f"orgName=&orgId=&tenderName={encoded_keyword}&tenderId=&"
            f"tenderType=TENDER_DECLARATION&tenderWay=TENDER_WAY_ALL_DECLARATION&"
            f"dateType=isSpdt&tenderStartDate={start_dt.strftime('%Y/%m/%d')}&"
            f"tenderEndDate={today.strftime('%Y/%m/%d')}&"
            f"radProctrgCate=RAD_PROCTRG_CATE_3&policyAdvocacy="
        )
        
        print("Fetching results...")
        response = scraper.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"HTTP Error {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.select_one("table.table_list") or soup.find("table", {"summary": "結果列表"})
        
        if not table:
            print("Table not found. (No results or blocked)")
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
                job_no = name_text.split("(")[1].split(")")[0] if "(" in name_text else name_text[:10]
                
                tenders.append({
                    "job_no": job_no,
                    "title": name_text,
                    "org": org,
                    "category": "勞務類",
                    "budget": cols[7].get_text(strip=True).replace(",", ""),
                    "publish": cols[5].get_text(strip=True).replace("/", ""),
                    "deadline": cols[6].get_text(strip=True),
                    "url": "https://web.pcc.gov.tw" + name_cell.find("a")["href"] if name_cell.find("a") else ""
                })
            except Exception: continue
                
        print(f"Success! Found {len(tenders)} items.")
        return tenders
    except Exception as e:
        print(f"Error: {e}")
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

if __name__ == "__main__":
    main()
