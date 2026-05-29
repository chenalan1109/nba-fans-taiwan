# CLAUDE.md — NBA FANS TAIWAN 專案參考文件

## 專案用途與技術限制

**NBA FANS TAIWAN** 是一個 NBA 球迷互動平台，以課程作業為背景開發，目前在 Milestone 10。

**技術棧**：
- Python 3.12 + Streamlit（單一語言限制，不引入 JS 框架或前端打包工具）
- SQLite（本地）/ Supabase Postgres（未來雲端，目前尚未接入）
- `nba_api`：官方 API wrapper
- `pandas` + `plotly`：資料處理與圖表
- `mypy` + `pytest`：型別檢查與測試

**執行方式**：
```bash
streamlit run app.py                  # 自動 API + fallback 模式
NBA_DATA_MODE=seed streamlit run app.py  # 強制 offline seed 資料（課堂 demo 用）
```

---

## 目錄結構

```
maurice.copy/
├── app.py                  # 主進入點：頁面路由、sidebar、app 初始化
├── requirements.txt        # 套件依賴
├── _pages/                 # 每個頁面模組，各自導出 render()
│   ├── home.py
│   ├── realtime_hub.py
│   ├── player_stats.py
│   ├── voting.py
│   ├── fantasy_team.py
│   └── matchup_debate.py
├── config/
│   └── settings.py         # 環境變數解析（APP_MODE、DATABASE_URL）
├── database/
│   ├── db.py               # SQLite 連線與查詢工具函數
│   ├── schema.sql          # 建表 SQL（CREATE TABLE IF NOT EXISTS）
│   └── seed_data.py        # 離線展示用硬編碼資料
├── models/
│   └── player.py           # Player frozen dataclass（其他 model 目前較少使用）
├── services/
│   ├── nba_api_service.py  # NBA 資料抓取（CDN → nba_api → seed 三層 fallback）
│   ├── player_service.py   # 球員查詢、fantasy 分數計算
│   ├── game_service.py     # 隊伍評分、fantasy 規則驗證、matchup 模擬
│   └── vote_service.py     # 投票 CRUD（polls/votes 表操作）
├── ui/
│   ├── theme.py            # Spurs 黑銀主題 CSS（以 st.markdown 注入）
│   ├── components.py       # 可重用 UI 元件（卡片、KPI strip、VS block 等）
│   └── charts.py           # Plotly 圖表建構函數
├── tests/                  # pytest 測試套件
├── scripts/                # demo_check.py、run_tests.sh 等開發工具
├── docs/                   # 雲端部署筆記
└── data/                   # SQLite DB 檔案（runtime 自動建立，gitignore）
```

---

## 五個功能模組

### 1. 即時資訊牆（Real-time Hub）
- **頁面**：`_pages/realtime_hub.py`
- **資料來源**：`services/nba_api_service.get_scoreboard()`
- **抓取順序（三層 fallback）**：
  1. `cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json`（直接 HTTP GET）
  2. `nba_api.live.nba.endpoints.scoreboard`（library）
  3. `database/seed_data.get_seed_scoreboard()`（hardcoded 3 筆靜態資料）
- **快取**：無 runtime 快取，每次 rerun 重新打 API
- **資料格式**：所有來源統一正規化為 `{game_date, home_team, away_team, status, home_score, away_score}`

### 2. 球員百科（Stats DB）
- **頁面**：`_pages/player_stats.py`
- **資料來源**：`services/player_service` → `services/nba_api_service`
- **流程**：
  - 搜尋：`nba_api.stats.static.players.find_players_by_full_name()` → fallback seed
  - 個人 profile：`nba_api.stats.endpoints.commonplayerinfo`
  - 生涯數據：`nba_api.stats.endpoints.playercareerstats`（取最近 5 季，換算 per-game）
- **視覺化**：近年趨勢折線圖、能力雷達圖（STL/BLK ×5 視覺化）、完整數據表
- **資料品質指標**：`player_service.get_player_data_quality()` 回傳 complete / partial / limited

### 3. 球迷投票（Voting）
- **頁面**：`_pages/voting.py`
- **儲存方式**：SQLite，`services/vote_service`
- **SQLite 表**：`polls`、`poll_options`、`votes`
- **防重複機制**：`votes` 表有 `UNIQUE(poll_id, voter_id)` 約束
- **投票身份**：用戶輸入暱稱字串作為 `voter_id`（非登入系統）
- **初始化**：每次渲染呼叫 `ensure_seed_polls()`，確保預設投票主題存在（冪等操作）

### 4. 模擬選秀（Fantasy Team）
- **頁面**：`_pages/fantasy_team.py`
- **球員池**：來自 `seed_data.get_seed_players()`（30+ 名球員硬編碼資料）
- **規則**：5 人陣容、Salary Cap = 100、同位置 ≤ 3 名
- **Salary 計算**：`fantasy_score / 4`（最低 1.0），fantasy_score = PTS + REB×1.2 + AST×1.5 + STL×2 + BLK×2 - TOV
- **儲存**：`services/game_service.save_fantasy_team()` 寫入 `fantasy_teams` + `fantasy_team_players` 表
- **本次 session 狀態**：owner/team name 暫存於 `st.session_state`

### 5. Matchup Debate
- **頁面**：`_pages/matchup_debate.py`
- **對戰資料**：`database/seed_data.get_seed_matchups()` 回傳 list，目前只有 1 筆（"Spurs Inspired Young Core vs NBA Superstars"），**設計為後續可擴充多筆**
- **目前 matchup 結構**：每筆含 `id`、`title`、`team_a_name`、`team_b_name`、`team_a_players`/`team_b_players`（球員姓名 list），從 `get_featured_players()` 的球員池對應
- **模擬模型**：`game_service.simulate_matchup()` 計算 team_power，公式為加權組合（PTS×0.4 + REB×0.2 + AST×0.2 + defense×0.2）
- **球迷投票**：SQLite `matchup_votes` 表，以 `matchup_id`（字串 slug）+ 暱稱為 `voter_id`，`UNIQUE(matchup_id, voter_id)` 防重複；**多筆 matchup 的投票天然隔離**
- **Tabs**：陣容卡片 / 數據對比（Plotly 橫條圖）/ 球迷投票（donut 圖）
- **擴充方式**：在 `seed_data.get_seed_matchups()` 新增 dict，並確保 id 唯一即可；頁面目前只取 `[0]`，擴充時需同步修改 `matchup_debate.py`

---

## 資料抓取與儲存

### 外部 API
- 即時比分：直接 HTTP GET cdn.nba.com（`requests` 套件，8 秒 timeout，帶 browser User-Agent header）
- 球員資料：`nba_api` 套件封裝
- 所有外部呼叫都有 try/except，失敗自動降級到 seed data
- 回傳格式統一為 `{"source": "api"|"partial_api"|"seed", "items": [...], "error": ...}`

### 本地 SQLite
- 路徑：`data/nba_fans_taiwan.db`（預設）或由 `DATABASE_URL=sqlite:///...` 指定
- 初始化：`database/db.init_db()` 在 app 啟動時執行（透過 `st.session_state["db_initialized"]` 確保只跑一次）
- 查詢工具：`db.execute_query()` / `db.fetch_all()` / `db.fetch_one()`

### 環境變數
| 變數 | 預設值 | 說明 |
|---|---|---|
| `NBA_DATA_MODE` | `auto` | `seed` 強制離線模式，適合課堂 demo |
| `APP_MODE` | `local` | `cloud` 模式改變投票說明文案 |
| `DATABASE_URL` | 無（用 data/ 路徑） | `sqlite:///...` 或 `postgresql://...` |

---

## Models 層說明

`models/` 下的 frozen dataclass 均為未來服務層型別化使用而預留，目前只有 `Player` 被 services 和 pages 廣泛引用：

| 檔案 | 欄位 | 目前使用狀況 |
|---|---|---|
| `player.py` | id, name, team, position, pts/reb/ast/stl/blk/tov, image_url | 全面使用 |
| `team.py` | id, name, abbreviation, conference | 預留，尚未引用 |
| `matchup.py` | id, title, team_a_name, team_b_name | 預留，matchup 目前以 dict 傳遞 |
| `vote.py` | id, poll_id, voter_id, option | 預留，vote 目前以 SQLite Row 傳遞 |
| `user.py` | （未讀，推測為 id, username） | 預留 |

---

## 程式慣例

- 所有檔案頭部 `from __future__ import annotations`（支援 3.10 以前語法）
- `Player` 是 frozen dataclass（不可變）；其他 model 是型別藍圖，尚待接入
- 頁面模組只導出一個 `render() -> None` 函數，由 `app.py` 統一呼叫
- UI 全部用 `ui/theme.py` 的 CSS class + `ui/components.py` 的函數，**不在頁面層直接寫 inline HTML**
- CSS 以 `st.markdown(unsafe_allow_html=True)` 注入，每次 rerun 都要重新注入（Streamlit 機制）
- 投票身份採用文字暱稱（非 session/cookie），同一暱稱在同一 poll 只能投一次（DB 層保證）
- type hints 全面使用，mypy strict 模式

---

## 可安全忽略的目錄

| 目錄/檔案 | 原因 |
|---|---|
| `.venv/` | Python 虛擬環境，不含程式邏輯 |
| `data/` | SQLite DB runtime 檔案，gitignore，自動建立 |
| `__pycache__/` | Python bytecode 快取 |
| `.streamlit/` | Streamlit 設定與快取（主題設定在 `config.toml`） |
| `scripts/` | demo_check、run_tests 等工具腳本，不含業務邏輯 |
| `docs/` | 雲端部署筆記，非程式碼 |
| `tests/` | 除非在修 bug 或加新功能，否則不需優先閱讀 |
