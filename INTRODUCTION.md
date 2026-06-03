# NBA FANS TAIWAN — 專案介紹

> 一個以球迷為中心的 NBA 互動平台，結合即時賽況、球員數據、幻想球隊與預測市場。

---

## 目錄

1. [專案概述](#專案概述)
2. [功能介紹](#功能介紹)
3. [技術架構](#技術架構)
4. [演算法與計算邏輯](#演算法與計算邏輯)
5. [資料來源](#資料來源)
6. [資料庫設計](#資料庫設計)
7. [部署環境](#部署環境)

---

## 專案概述

**NBA FANS TAIWAN** 是一個以 Streamlit 建構的 NBA 球迷互動平台，提供即時賽況查詢、球員數據分析、幻想球隊組建、先知幣預測市場與社群投票等功能。介面採用馬刺隊風格的黑銀配色，支援本地端（SQLite）與雲端（PostgreSQL / Supabase）雙模式部署。

---

## 功能介紹

### 1. 首頁（Home）
- 顯示本賽季 KPI（賽季階段、比賽場次）
- 即時抓取今日得分王，作為亮點人物展示
- 季後賽期間顯示對戰括號；例行賽期間顯示東西區積分榜
- 提供各功能頁面的快速入口卡片

### 2. 登入 / 註冊（Auth）
- 帳號註冊：用戶名（4–30 字元）、暱稱（公開顯示）、密碼（至少 4 字元）
- SHA-256 密碼雜湊，無明文儲存
- 新帳號自動獲得 **1,000 先知幣**
- 支援登入後修改密碼，側邊欄顯示當前幣值餘額

### 3. 即時資訊牆（Realtime Hub）
- **今日賽程** 與 **近 7 天賽事** 兩分頁
- 比賽卡片顯示主客隊得分、比賽狀態（進行中 / 結束 / 未開賽）
- 展開詳細框分統計（命中率、三分、罰球）
- **球員評分**：1–5 星評分，顯示多人平均星級
- **裁判評分**：依球衣號碼對主裁評分
- **留言系統**：發文、按讚、刪除（管理員可刪除所有留言）

### 4. 球員百科（Player Stats）
- 以球員姓名搜尋（預設：Curry）
- 展示近 5 個賽季每場平均數據
- **三種視覺化圖表**：
  - 折線趨勢圖（得分 / 籃板 / 助攻隨賽季變化）
  - 雷達圖（五維度：PTS / REB / AST / STL×5 / BLK×5）
  - 數據表格檢視
- 資料品質指標：complete / partial / limited

### 5. 球迷投票 · 先知幣預測（Voting）

最核心的互動系統，包含五個分頁：

| 分頁 | 功能 |
|------|------|
| 球員殿堂 | 常設球迷投票（史上最強防守者、GOAT 等），管理員可新增問題 |
| 即時預測 | 季後賽晉級預測（系列賽開打後鎖單，贏得 200 基礎幣） |
| 長期預測 | 年度獎項預測（MVP、總冠軍、最佳防守等，贏得 1,000 基礎幣） |
| 我的紀錄 | 個人預測歷史，顯示狀態、正確答案與已獲幣值 |
| 排行榜 | 先知幣前 20 名用戶，管理員可調整幣值並結算獎項 |

**先知幣取得途徑**：
- 註冊獎勵：1,000 幣
- 每日簽到：150 幣（每天一次）
- 正確預測：幣值依預測時間早晚遞減（越早預測越高）

### 6. 幻想球隊（Fantasy Team）

| 分頁 | 功能 |
|------|------|
| 球員市場 | 依姓名、球隊、位置篩選，消耗先知幣購買球員 |
| 我的球員池 | 已購買球員的卡片 / 表格兩種檢視模式 |
| 組建幻想隊伍 | 從球員池選出 5 人，受薪資帽與位置限制 |

**薪資帽規則**：
- 預設薪資帽：100 單位
- 每名球員薪資 = `max(1.0, fantasy_score / 4)`
- 同位置（PG/SG/SF/PF/C）最多 3 人
- 球員購買價格 = `max(30, int(fantasy_score × 3))` 先知幣

### 7. Matchup Debate
- 球迷自訂 5v5 對戰（每隊 1–5 人，雙方人數須相同）
- 並排數據比較：PPG / RPG / APG / SPG / BPG
- Plotly 水平條形圖視覺化兩隊能力差距
- 球迷投票支持哪隊，圓環圖顯示票數分佈
- 內建**勝率模擬器**（規則式模型）

---

## 技術架構

### 前端 / UI
| 工具 | 用途 |
|------|------|
| **Streamlit** | 網頁框架，多頁路由與組件渲染 |
| **Plotly** | 互動式圖表（折線、雷達、條形、圓環圖） |
| **自定義 CSS** | 馬刺風黑銀主題，注入 `st.markdown(unsafe_allow_html=True)` |

### 後端 / 資料
| 工具 | 用途 |
|------|------|
| **Python 3.x** | 主要開發語言 |
| **nba_api** | 官方 NBA Stats API 封裝庫 |
| **requests** | 直接請求 NBA CDN 實時 JSON |
| **pandas** | 數據清理與表格處理 |
| **sqlite3** | 本地端資料庫（內建標準庫） |
| **psycopg2** | 雲端 PostgreSQL 連接器 |
| **hashlib** | SHA-256 密碼雜湊（內建標準庫） |

### 開發工具
| 工具 | 用途 |
|------|------|
| **pytest** | 單元測試框架 |
| **mypy** | 靜態型別檢查（strict 模式） |

---

## 演算法與計算邏輯

### Fantasy Score（幻想球員評分）

```
fantasy_score = PTS + REB×1.2 + AST×1.5 + STL×2 + BLK×2 - TOV
```

用於：球員排行、市場定價、薪資換算、幻想隊伍總分計算。

---

### 勝率模擬（Matchup 模型）

```
defense_score  = avg_STL×2 + avg_BLK×2
team_power     = avg_PTS×0.4 + avg_REB×0.2 + avg_AST×0.2 + defense_score×0.2
win_rate_A (%) = team_A_power / (team_A_power + team_B_power) × 100
```

加權比例：進攻 40%、籃板 20%、助攻 20%、防守 20%。

---

### 先知幣時間衰減（指數遞減）

```
coins_earned = base_coins × e^(−λ × days_since_open)
```

| 參數 | 數值 |
|------|------|
| `base_coins`（長期預測） | 1,000 |
| `base_coins`（即時預測） | 200 |
| `λ`（衰減率） | 4.0 |

越早預測可獲得越多幣值，鼓勵球迷在資訊少時勇敢下注。

---

### 球員市場定價

```
price = max(30, int(fantasy_score × 3))    # 購買價格（先知幣）
salary = max(1.0, fantasy_score / 4)        # 幻想隊薪資單位
```

---

### 雷達圖維度縮放

STL 與 BLK 數據乘以 5 倍後才繪製雷達圖，使得防守數值在視覺上與得分、籃板等數據保持可比性。

---

### 裁判 ID 生成

```python
referee_id = MD5(game_id + referee_name)[:8]
```

用 MD5 雜湊確保同一場比賽的同一裁判每次載入均有穩定唯一 ID，不需額外資料庫欄位。

---

## 資料來源

### 三層備援機制

```
[第一層] NBA CDN JSON（最快）
    ↓ 失敗
[第二層] nba_api 函式庫（最完整）
    ↓ 失敗
[第三層] 本地種子資料（永遠可用，離線模式）
```

| 層級 | 來源 | 資料內容 |
|------|------|----------|
| CDN | `cdn.nba.com/static/json/liveData/scoreboard/...` | 即時賽況 JSON |
| nba_api | NBA Stats 官方 API | 球員資料、職業生涯統計、比賽紀錄 |
| 種子資料 | `database/seed_data.py`（硬編碼） | 30+ 球員、3 場比賽範本、季後賽模擬資料 |

---

## 資料庫設計

共 **18 張資料表**，分為六大模組：

| 模組 | 資料表 | 說明 |
|------|--------|------|
| 使用者 | `user_accounts`, `users`, `daily_checkins`, `user_player_pool` | 帳號、簽到、球員收藏 |
| 投票 | `polls`, `poll_options`, `votes` | 可結算的動態問卷 |
| 殿堂投票 | `hall_poll_definitions`, `hall_votes` | 長期常設投票問題 |
| 先知幣 | `prophet_users`, `prediction_items`, `user_predictions`, `settlement_events` | 預測市場與幣值帳本 |
| 幻想球隊 | `fantasy_teams`, `fantasy_team_players` | 球隊組建與名單 |
| 對戰 / 社群 | `custom_matchups`, `matchup_votes`, `player_ratings`, `game_comments`, `comment_likes` | 對戰建立、評分、留言互動 |

**資料庫雙模式**：
- 本地開發：SQLite（`data/nba_fans_taiwan.db`）
- 雲端部署：PostgreSQL（Supabase），使用 `BIGSERIAL` 與 `TIMESTAMPTZ`

---

## 部署環境

| 環境變數 | 說明 | 預設值 |
|----------|------|--------|
| `APP_MODE` | `local` 或 `cloud` | `local` |
| `NBA_DATA_MODE` | `auto`（API優先）或 `seed`（離線） | `auto` |
| `DATABASE_URL` | SQLite 路徑或 PostgreSQL 連線字串 | SQLite |
| `ADMIN_USERNAME` | 管理員帳號 | `admin` |
| `ADMIN_PASSWORD` | 管理員密碼 | `admin` |

**服務層架構**（`services/` 目錄）：

```
nba_api_service.py  — 資料抓取（三層備援）
player_service.py   — 球員查詢與 Fantasy Score
game_service.py     — 對戰模擬與隊伍驗證
prophet_service.py  — 先知幣預測生命週期
market_service.py   — 球員定價與幣值管理
auth_service.py     — 帳號認證
vote_service.py     — 問卷與投票
hall_service.py     — 殿堂問卷管理
comment_service.py  — 留言與按讚
rating_service.py   — 球員 / 裁判評分聚合
season_service.py   — 賽季階段偵測
checkin_service.py  — 每日簽到邏輯
cached.py           — Streamlit @st.cache_data（TTL 24h / 1h）
```
