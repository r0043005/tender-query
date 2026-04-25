# 政府電子採購網 - 標案查詢工具

一個簡潔的網頁工具，用於查詢台灣政府電子採購網的標案資訊。

## 功能特色

- 🔍 關鍵字搜尋 - 支援任意關鍵字查詢
- 📋 勞務採購篩選 - 預設顯示勞務採購類型
- ⏰ 等標期篩選 - 只顯示投標期限內的標案
- 📅 自動更新 - GitHub Actions 每日自動抓取最新資料
- 📱 響應式設計 - 支援手機和桌面裝置

## 使用方式

### 線上使用

直接訪問 GitHub Pages 部署的版本即可使用。

### 本地開發

```bash
# 進入專案目錄
cd tender-query

# 使用 Python 啟動本地伺服器
python -m http.server 8000

# 或使用 npx
npx serve .
```

然後在瀏覽器中開啟 `http://localhost:8000`

## 資料來源與自動更新

本專案使用 **GitHub Actions** 每日自動從政府電子採購網抓取最新標案資料：

1. **資料檔案**：`data/tenders.json` - 每日自動更新
2. **更新頻率**：每天午夜執行一次（可手動觸發）
3. **備援來源**：若 API 無法取得資料，會使用本地上次更新的資料

### 手動更新資料

1. 進入 GitHub 儲存庫的 **Actions** 頁面
2. 點擊 **Fetch Daily Tenders** 工作流程
3. 點擊 **Run workflow** 手動執行

## 部署到 GitHub Pages

### 自動部署

推送到 `main` 分支即可自動部署到 GitHub Pages。

### 啟用 GitHub Pages

1. 進入儲存庫 `Settings` → `Pages`
2. `Source` 選擇 `GitHub Actions`
3. 儲存後即可透過 `https://您的用戶名.github.io/儲存庫名稱` 訪問

## 專案結構

```
tender-query/
├── index.html              # 主程式
├── README.md               # 說明文件
├── data/
│   └── tenders.json        # 每日更新的標案資料
├── scripts/
│   └── fetch_tenders.py   # 資料抓取腳本
└── .github/
    └── workflows/
        ├── deploy.yml     # 部署工作流程
        └── daily-fetch.yml # 每日抓取工作流程
```

## 技術架構

- 純前端 HTML/CSS/JavaScript
- 無需後端伺服器
- 使用 Fetch API 取得本地 JSON 資料
- CSS Grid 和 Flexbox 響應式佈局

## 相關連結

- [政府電子採購網](https://web.pcc.gov.tw/)
- [pcc.mlwmlw.org](https://pcc.mlwmlw.org/) - 標案資料 API
- [mlwmlw/pcc GitHub](https://github.com/mlwmlw/pcc)
