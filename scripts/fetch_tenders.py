#!/usr/bin/env python3
import sys
import os
import cloudscraper
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime, timedelta
import argparse

def fetch_tenders_by_scraping(keyword="清"):
    print(f"開始爬取關鍵字: {keyword}")
    
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )
    
    # 建立與瀏覽器一致的 Headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://web.pcc.gov.tw/prkms/tender/common/basic/indexTenderBasic"
    }
    
    try:
        # 步驟 1: 存取首頁獲取 Cookie
        print("存取首頁中...")
        scraper.get("https://web.pcc.gov.tw/prkms/tender/common/basic/indexTenderBasic", headers=headers, timeout=20)
        time.sleep(2) # 延遲 2 秒模擬真人
        
        # 步驟 2: 使用您提供成功的完整 URL
        # 我們將關鍵字進行 URL 編碼
        import urllib.parse
        encoded_keyword = urllib.parse.quote(keyword)
        
        today = datetime.now()
        start_dt = today - timedelta(days=14) # 搜尋兩週
        
        target_url = (
            f"https://web.pcc.gov.tw/prkms/tender/common/basic/readTenderBasic?"
            f"pageSize=50&firstSearch=true&searchType=basic&isBinding=N&isLogIn=N&level_1=on&"
            f"orgName=&orgId=&tenderName={encoded_keyword}&tenderId=&"
            f"tenderType=TENDER_DECLARATION&tenderWay=TENDER_WAY_ALL_DECLARATION&"
            f"dateType=isSpdt&tenderStartDate={start_dt.strftime('%Y/%m/%d')}&"
            f"tenderEndDate={today.strftime('%Y/%m/%d')}&"
            f"radProctrgCate=RAD_PROCTRG_CATE_3&policyAdvocacy="
        )
        
        print(f"發送請求到成功 URL: {target_url}")
        response = scraper.get(target_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"錯誤: 狀態碼 {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.select_one("table.table_list") or soup.find("table", {"summary": "結果列表"})
        
        if not table:
            print("找不到表格，這可能是因為 Cloudflare 的驗證頁面或是查無資料。")
            print(f"Page Title: {soup.title.string if soup.title else 'No Title'}")
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
                
                job_no = name_text.split("(")[1].split(")")[0] if "(" in name_text else name_text[:15]
                name = name_text.split(")")[1].strip() if ")" in name_text else name_text
                
                tenders.append({
                    "job_no": job_no,
                    "title": name,
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

if __name__ == "__main__":
    main()
