#!/usr/bin/env python3
"""
政府電子採購網標案資料抓取腳本 (Session 強化版)
使用 Session 處理 Cookie 並強化 HTML 解析
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import time
from datetime import datetime, timedelta
import argparse

def fetch_tenders_by_scraping(keyword="清"):
    print(f"開始爬取關鍵字: {keyword}")
    
    # 使用 Session 保持 Cookies
    session = requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    try:
        # 第一步：先訪問首頁建立 Session
        print("存取搜尋首頁建立 Session...")
        index_url = "https://web.pcc.gov.tw/prkms/tender/common/basic/indexTenderBasic"
        session.get(index_url, headers=headers, timeout=20)
        
        # 第二步：執行搜尋
        url = "https://web.pcc.gov.tw/prkms/tender/common/basic/readTenderBasic"
        
        today = datetime.now()
        start_dt = today - timedelta(days=10) # 稍微放寬日期範圍增加命中率
        
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
            "dateType": "isSpdt",
            "tenderStartDate": start_dt.strftime("%Y/%m/%d"),
            "tenderEndDate": today.strftime("%Y/%m/%d"),
            "radProctrgCate": "RAD_PROCTRG_CATE_3",
        }
        
        print(f"發送搜尋請求到 {url}...")
        headers["Referer"] = index_url
        response = session.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"錯誤: 狀態碼 {response.status_code}")
            return []
            
        # 偵錯：如果沒抓到資料，存下 HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 標案列表解析邏輯
        # 採購網結果表格可能在 class="table_list" 或特定 id 下
        table = soup.select_one("table.table_list")
        if not table:
            table = soup.find("table", {"summary": "結果列表"})
        
        if not table:
            # 檢查是否有查無資料訊息
            if "查無資料" in response.text:
                print("結果：查無符合條件的標案。")
            else:
                print("警告：找不到表格結構。")
                # 儲存 HTML 片段供開發者查閱
                with open("error_page.html", "w", encoding="utf-8") as f:
                    f.write(response.text[:5000])
                print("已存檔前 5000 字元至 error_page.html")
            return []
            
        rows = table.find_all("tr")
        tenders = []
        
        for row in rows:
            cols = row.find_all("td")
            # 通常標案資料列會有超過 5 個 td
            if len(cols) < 7:
                continue
            
            try:
                # 索引位置可能因版本微調，我們進行更寬鬆的解析
                # 嘗試找出包含 <a> 標籤且內容有關鍵字的列
                name_cell = None
                for td in cols:
                    if td.find("a") and keyword in td.get_text():
                        name_cell = td
                        break
                
                if not name_cell:
                    name_cell = cols[2] # 預設位置
                
                org = cols[1].get_text(strip=True)
                name_text = name_cell.get_text(strip=True)
                
                job_no = ""
                name = name_text
                if "(" in name_text and ")" in name_text:
                    job_no = name_text.split("(")[1].split(")")[0]
                    name = name_text.split(")")[1].strip() if ")" in name_text else name_text
                
                # 找到日期欄位（通常是 YYYY/MM/DD 或 民國格式）
                publish = ""
                for td in cols:
                    txt = td.get_text(strip=True)
                    if "/" in txt and len(txt) >= 8:
                        publish = txt.replace("/", "")
                        break

                tenders.append({
                    "job_no": job_no or name_text[:15],
                    "title": name,
                    "org": org,
                    "category": "勞務類",
                    "budget": 0, # 此頁面預算有時在詳細頁，先給 0
                    "publish": publish,
                    "deadline": "",
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
