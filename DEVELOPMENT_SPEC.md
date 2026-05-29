# NBA FANS TAIWAN 開發規格文件

版本：MVP 規劃版  
建議技術棧：Python + Streamlit + SQLite + nba_api  
適用情境：商管程式設計課程專案、期末展示、多人分工實作

## 1. 專案定位

NBA FANS TAIWAN 是一個以 Python 與 Streamlit 建立的 NBA 球迷互動資料平台，目標使用者是台灣 NBA 球迷。平台的核心不是做大型商業網站，而是用課程專案可負擔的規模，展示資料擷取、資料庫操作、視覺化、互動投票與簡易遊戲邏輯。

使用者可以在平台上完成以下任務：

1. 查看 NBA 賽程、比分與即時資訊牆。
2. 搜尋球員與球隊資料。
3. 查看球員或球隊數據圖表。
4. 參與 MVP、總冠軍、單場勝負等預測投票。
5. 建立自己的 Fantasy Team。
6. 自訂或參與 Matchup Debate。
7. 在進階版本中使用虛擬 NBA 幣、球員卡與市場功能。

## 2. 專案限制

本專案必須遵守以下原則：

1. 主要程式語言使用 Python。
2. UI 優先使用 Streamlit。
3. 資料庫優先使用 SQLite。
4. NBA 資料來源優先使用 `nba_api`。
5. 必須有 API 失效時的 fallback seed data，避免 demo 因網路或 API 問題中斷。
6. 架構要適合課程專案，不導入過重框架或複雜微服務。
7. 優先完成 MVP，再做進階功能。
8. UI、資料庫、資料抓取、投票與遊戲邏輯必須分層。
9. 必須加入 pytest 測試規劃。
10. 必須加入 mypy 型別檢查規劃。
11. 文件目標是讓不同組員可以依照分工開始實作。

## 3. MVP 與進階功能切分

### 3.1 MVP 必做功能

MVP 的標準是「可以穩定 demo，且每一頁都有可展示的核心互動」。

| 功能 | 頁面 | MVP 行為 | 資料來源 |
| --- | --- | --- | --- |
| 首頁 | `home.py` | 顯示平台介紹、快速入口、今日焦點 | 本地設定或 seed data |
| 即時資訊牆 | `realtime_hub.py` | 顯示近期賽程、比分、熱門球隊資訊 | `nba_api`，失敗時 seed data |
| 球員百科 | `player_stats.py` | 搜尋球員、顯示基本資料與簡單圖表 | `nba_api`，失敗時 seed data |
| 球迷投票 | `voting.py` | MVP、總冠軍、單場勝負投票與結果統計 | SQLite |
| Fantasy Team | `fantasy_team.py` | 選 5 名球員組隊，計算簡易總分 | seed data 或快取球員資料 |
| Matchup Debate | `matchup_debate.py` | 左右兩隊比較、投票、簡易勝率或分數模擬 | SQLite + 遊戲邏輯 |

### 3.2 進階功能

進階功能只在 MVP 穩定後開發：

1. 使用者登入與個人檔案。
2. 虛擬 NBA 幣。
3. 球員卡收藏與市場。
4. 每日任務、連續登入獎勵。
5. 社群分享連結。
6. 更完整的球隊與球員資料視覺化。
7. 投票排行榜與歷史紀錄。

### 3.3 暫不實作項目

為避免過度工程化，以下項目不列入課程 MVP：

1. 真實金流。
2. 複雜權限系統。
3. 即時多人聊天室。
4. 大型前後端分離架構。
5. 雲端部署自動化流程。
6. 高精準賽事預測模型。

## 4. 建議專案結構

建議將目前集中在單一檔案的原型逐步重構成以下結構：

```text
nba-fans-taiwan/
│
├── app.py
│
├── pages/
│   ├── __init__.py
│   ├── home.py
│   ├── realtime_hub.py
│   ├── player_stats.py
│   ├── voting.py
│   ├── fantasy_team.py
│   └── matchup_debate.py
│
├── services/
│   ├── __init__.py
│   ├── nba_api_service.py
│   ├── player_service.py
│   ├── vote_service.py
│   └── game_service.py
│
├── database/
│   ├── __init__.py
│   ├── db.py
│   ├── schema.sql
│   └── seed_data.py
│
├── models/
│   ├── __init__.py
│   ├── player.py
│   ├── team.py
│   ├── user.py
│   ├── vote.py
│   └── matchup.py
│
├── tests/
│   ├── test_player_service.py
│   ├── test_vote_service.py
│   ├── test_game_service.py
│   └── test_database.py
│
├── scripts/
│   ├── run_tests.sh
│   └── type_check.sh
│
├── requirements.txt
├── pyproject.toml
├── README.md
└── DEVELOPMENT_SPEC.md
```

### 4.1 分層責任

| 層級 | 目錄 | 責任 |
| --- | --- | --- |
| UI 層 | `app.py`, `pages/` | Streamlit 畫面、按鈕、表格、圖表、session state |
| Service 層 | `services/` | 資料查詢、投票邏輯、遊戲邏輯、API fallback |
| Database 層 | `database/` | SQLite 連線、建表、查詢、seed data |
| Model 層 | `models/` | `dataclass` 或型別定義，讓資料結構清楚 |
| Test 層 | `tests/` | pytest 單元測試與資料庫測試 |

UI 層不應直接寫 SQL，也不應直接呼叫大量 `nba_api` endpoint。UI 應呼叫 service function，再由 service 決定要走 API、資料庫或 seed data。

## 5. 檔案職責設計

### 5.1 `app.py`

主入口，負責：

1. 設定 Streamlit 頁面。
2. 初始化資料庫。
3. 設定 sidebar 導航。
4. 根據選單載入對應 page function。

建議每個頁面都提供一個 `render()` function，例如：

```python
from pages import home, realtime_hub, player_stats

def main() -> None:
    selected_page = st.sidebar.radio(...)
    if selected_page == "首頁":
        home.render()
```

### 5.2 `pages/home.py`

首頁，負責：

1. 顯示專案名稱 NBA FANS TAIWAN。
2. 顯示今日焦點或熱門球員。
3. 提供進入主要功能的導覽。
4. 不處理資料庫與複雜商業邏輯。

### 5.3 `pages/realtime_hub.py`

即時資訊牆，負責：

1. 顯示近期賽程。
2. 顯示比分或比賽狀態。
3. 顯示熱門球隊或球員資訊。
4. 呼叫 `services.nba_api_service` 取得資料。
5. API 失敗時顯示 fallback seed data 並提示「目前使用展示資料」。

### 5.4 `pages/player_stats.py`

球員百科與數據視覺化，負責：

1. 提供球員搜尋輸入框。
2. 顯示球員基本資料。
3. 顯示球員近年數據表格。
4. 顯示折線圖、長條圖或雷達圖。
5. 呼叫 `player_service`，不直接連 API。

MVP 圖表建議：

1. 場均得分 PPG 折線圖。
2. 籃板 REB 與助攻 AST 長條圖。
3. 命中率 FG% 指標卡。

### 5.5 `pages/voting.py`

球迷投票頁，負責：

1. 顯示投票主題，例如 MVP 預測、總冠軍預測。
2. 讓使用者選擇選項。
3. 將投票寫入 SQLite。
4. 顯示投票統計圖。

MVP 可先不做完整帳號系統，而是使用簡易 `session_id` 或讓使用者輸入暱稱，避免同一使用者重複投票。

### 5.6 `pages/fantasy_team.py`

Fantasy Team 頁，負責：

1. 顯示可選球員清單。
2. 讓使用者選擇 5 名球員。
3. 計算隊伍總分。
4. 顯示隊伍平均數據。

MVP 計分公式：

```text
fantasy_score = points + rebounds * 1.2 + assists * 1.5 + steals * 2 + blocks * 2 - turnovers
```

這個公式簡單、可解釋，適合課程展示。

### 5.7 `pages/matchup_debate.py`

Matchup Debate 頁，負責：

1. 左右兩隊球員展示。
2. 顯示兩隊平均數據比較。
3. 讓使用者投票支持 Team A 或 Team B。
4. 顯示全球投票比例。
5. 顯示簡易模擬結果。

MVP 模擬公式可使用：

```text
team_power = avg_points * 0.4 + avg_rebounds * 0.2 + avg_assists * 0.2 + avg_defense_score * 0.2
```

進階版再增加位置、球風、化學效應等因素。

## 6. Service 層設計

### 6.1 `services/nba_api_service.py`

負責與 `nba_api` 溝通。所有外部 API 呼叫應集中在這個檔案。

建議 function：

```python
def get_scoreboard() -> list[dict]:
    ...

def search_players(keyword: str) -> list[dict]:
    ...

def get_player_profile(player_id: int) -> dict:
    ...

def get_player_season_stats(player_id: int) -> list[dict]:
    ...
```

設計重點：

1. 每個 function 都要有 try/except。
2. API 失敗時回傳 seed data。
3. function 回傳格式要固定，讓 UI 不需要知道資料來自 API 或 fallback。
4. 可使用 `st.cache_data` 或 service 內部快取減少 API 呼叫。
5. 不在 service 內直接渲染 Streamlit UI。

### 6.2 `services/player_service.py`

負責球員資料整理。

建議 function：

```python
def find_players(keyword: str) -> list[Player]:
    ...

def get_player_detail(player_id: int) -> Player:
    ...

def get_player_chart_data(player_id: int) -> dict:
    ...

def calculate_fantasy_score(player: Player) -> float:
    ...
```

職責：

1. 將 `nba_api_service` 的 dict 轉成 `Player` model。
2. 補齊缺失欄位。
3. 整理給圖表使用的資料。
4. 提供 Fantasy Team 使用的分數。

### 6.3 `services/vote_service.py`

負責所有投票相關邏輯。

建議 function：

```python
def create_poll(title: str, options: list[str]) -> int:
    ...

def submit_vote(poll_id: int, voter_id: str, option: str) -> bool:
    ...

def get_vote_summary(poll_id: int) -> dict[str, int]:
    ...

def has_voted(poll_id: int, voter_id: str) -> bool:
    ...
```

規則：

1. 同一個 `voter_id` 對同一投票只能投一次。
2. 已投票時應回傳 `False` 或清楚錯誤狀態。
3. UI 只負責顯示，不直接操作 SQL。

### 6.4 `services/game_service.py`

負責 Fantasy Team 與 Matchup Debate 的遊戲邏輯。

建議 function：

```python
def calculate_team_score(players: list[Player]) -> float:
    ...

def compare_teams(team_a: list[Player], team_b: list[Player]) -> dict:
    ...

def simulate_matchup(team_a: list[Player], team_b: list[Player]) -> dict:
    ...
```

回傳格式範例：

```python
{
    "team_a_score": 86.5,
    "team_b_score": 81.2,
    "winner": "Team A",
    "reason": "Team A has higher scoring and assist rating."
}
```

## 7. Model 設計

MVP 建議使用 `dataclasses`，比 ORM 更簡單，也適合課程專案。

### 7.1 `models/player.py`

建議欄位：

```python
from dataclasses import dataclass

@dataclass
class Player:
    id: int
    name: str
    team: str
    position: str
    points: float
    rebounds: float
    assists: float
    steals: float = 0.0
    blocks: float = 0.0
    turnovers: float = 0.0
    image_url: str | None = None
```

### 7.2 `models/team.py`

```python
@dataclass
class Team:
    id: int
    name: str
    abbreviation: str
    conference: str | None = None
```

### 7.3 `models/user.py`

MVP 可以先使用簡化 user model：

```python
@dataclass
class User:
    id: int
    username: str
```

密碼登入不是 MVP 必要項。若要做登入，密碼不可明文儲存，至少使用 `hashlib` 或 `passlib`。

### 7.4 `models/vote.py`

```python
@dataclass
class Vote:
    id: int
    poll_id: int
    voter_id: str
    option: str
```

### 7.5 `models/matchup.py`

```python
@dataclass
class Matchup:
    id: int
    title: str
    team_a_name: str
    team_b_name: str
```

## 8. SQLite 資料庫設計

### 8.1 資料庫檔案

建議預設使用：

```text
data/nba_fans_taiwan.db
```

若不想新增 `data/` 目錄，也可先使用：

```text
nba_fans_taiwan.db
```

但不要再使用過於籠統的 `users.db`，因為未來不只存使用者。

### 8.2 `database/db.py`

負責：

1. 建立 SQLite 連線。
2. 執行 `schema.sql`。
3. 提供簡單 query helper。
4. 測試時允許傳入 temporary database path。

建議 function：

```python
def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    ...

def init_db(db_path: str | None = None) -> None:
    ...

def execute_query(sql: str, params: tuple = ()) -> None:
    ...

def fetch_all(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    ...
```

### 8.3 `database/schema.sql`

MVP 建議 schema：

```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS polls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS poll_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    poll_id INTEGER NOT NULL,
    option_text TEXT NOT NULL,
    FOREIGN KEY (poll_id) REFERENCES polls(id)
);

CREATE TABLE IF NOT EXISTS votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    poll_id INTEGER NOT NULL,
    voter_id TEXT NOT NULL,
    option_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (poll_id, voter_id),
    FOREIGN KEY (poll_id) REFERENCES polls(id),
    FOREIGN KEY (option_id) REFERENCES poll_options(id)
);

CREATE TABLE IF NOT EXISTS fantasy_teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_name TEXT NOT NULL,
    team_name TEXT NOT NULL,
    total_score REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fantasy_team_players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fantasy_team_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    player_name TEXT NOT NULL,
    FOREIGN KEY (fantasy_team_id) REFERENCES fantasy_teams(id)
);

CREATE TABLE IF NOT EXISTS matchup_votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    matchup_id TEXT NOT NULL,
    voter_id TEXT NOT NULL,
    selected_side TEXT NOT NULL CHECK (selected_side IN ('A', 'B')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (matchup_id, voter_id)
);
```

### 8.4 進階版 schema

進階功能可新增：

```sql
CREATE TABLE IF NOT EXISTS wallet_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    amount INTEGER NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS player_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_name TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    player_name TEXT NOT NULL,
    rarity TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS market_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER NOT NULL,
    seller_name TEXT NOT NULL,
    price INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (card_id) REFERENCES player_cards(id)
);
```

## 9. Fallback Seed Data 機制

### 9.1 為什麼需要 fallback

期末 demo 常見風險：

1. 教室網路不穩。
2. `nba_api` endpoint 暫時失效。
3. API 回應格式變動。
4. 呼叫太多次導致速度變慢。
5. 當天沒有比賽，畫面看起來空白。

因此所有核心頁面都必須能在沒有外部 API 的情況下展示。

### 9.2 `database/seed_data.py`

seed data 應提供：

1. 近期賽程範例。
2. 球員基本資料範例。
3. 球員賽季數據範例。
4. 預設投票主題。
5. 預設 Matchup Debate。

建議 function：

```python
def get_seed_scoreboard() -> list[dict]:
    ...

def get_seed_players() -> list[dict]:
    ...

def get_seed_player_stats(player_id: int) -> list[dict]:
    ...

def get_seed_polls() -> list[dict]:
    ...

def get_seed_matchups() -> list[dict]:
    ...
```

### 9.3 fallback 規則

所有 API service function 應遵守相同規則：

1. 先嘗試呼叫 `nba_api`。
2. 成功時將資料轉成內部固定格式。
3. 失敗時記錄錯誤原因。
4. 回傳 seed data。
5. 回傳結果中加入 `source` 欄位，值為 `api` 或 `seed`。

範例回傳：

```python
{
    "source": "seed",
    "items": [
        {
            "home_team": "Los Angeles Lakers",
            "away_team": "Golden State Warriors",
            "status": "Final",
            "home_score": 112,
            "away_score": 108
        }
    ]
}
```

UI 若收到 `source == "seed"`，應在頁面上用 `st.info()` 顯示：

```text
目前使用展示資料，外部 NBA API 暫時無法連線。
```

## 10. Streamlit UI 設計原則

### 10.1 導航

建議使用 sidebar：

```text
NBA FANS TAIWAN
├── 首頁
├── 即時資訊牆
├── 球員百科
├── 球迷投票
├── Fantasy Team
└── Matchup Debate
```

### 10.2 Session State

適合存在 `st.session_state` 的資料：

1. 使用者暱稱。
2. Fantasy Team 暫存球員。
3. 目前選擇的 matchup。
4. 是否已初始化資料庫。

不適合存在 session state 的資料：

1. 投票總結果。
2. 資料庫主要資料。
3. 大量球員資料。

### 10.3 圖表

MVP 優先使用 Streamlit 內建圖表：

1. `st.line_chart`
2. `st.bar_chart`
3. `st.metric`
4. `st.dataframe`

若時間足夠，再使用 Plotly：

```text
plotly
```

Plotly 適合做：

1. 多指標比較。
2. 雷達圖。
3. 互動式折線圖。

## 11. 依賴套件

### 11.1 `requirements.txt`

MVP 建議：

```text
streamlit
pandas
nba_api
pytest
mypy
types-requests
```

若要使用 Plotly：

```text
plotly
```

若要較安全地處理密碼：

```text
passlib
```

### 11.2 `pyproject.toml`

建議設定：

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]

[tool.mypy]
python_version = "3.11"
strict = false
warn_unused_ignores = true
warn_return_any = true
disallow_untyped_defs = true
ignore_missing_imports = true
```

`strict = false` 是因為課程專案需要兼顧開發速度。若後期穩定，可逐步改嚴格。

## 12. 測試規劃

### 12.1 測試原則

MVP 測試重點：

1. Service 層邏輯要測。
2. Database 層 CRUD 要測。
3. Streamlit UI 不必全面自動化測試。
4. 外部 API 不應在單元測試中真的呼叫。
5. 測試應使用 temporary SQLite database。

### 12.2 `tests/test_player_service.py`

測試項目：

1. 搜尋球員時可回傳符合 keyword 的球員。
2. API 失敗時會回傳 seed players。
3. fantasy score 計算正確。
4. 缺少部分數據時不會 crash。

### 12.3 `tests/test_vote_service.py`

測試項目：

1. 可以建立投票。
2. 可以提交投票。
3. 同一 voter 不能重複投同一 poll。
4. 可以正確統計票數。

### 12.4 `tests/test_game_service.py`

測試項目：

1. 五名球員可以計算隊伍分數。
2. Team A 分數高於 Team B 時 winner 正確。
3. 空隊伍或不足五人時有合理錯誤處理。
4. matchup 回傳格式包含 `team_a_score`、`team_b_score`、`winner`。

### 12.5 `tests/test_database.py`

測試項目：

1. `init_db()` 可以建立所有 MVP 資料表。
2. votes 的 UNIQUE constraint 正常運作。
3. poll options foreign key 關係正確。
4. temporary database 不會污染正式 demo database。

### 12.6 執行指令

```bash
pytest
```

或：

```bash
bash scripts/run_tests.sh
```

Windows PowerShell 可直接使用：

```powershell
pytest
```

## 13. mypy 型別檢查規劃

### 13.1 型別標註範圍

必須加型別的地方：

1. `services/` 所有 public function。
2. `database/db.py` 所有 function。
3. `models/` 所有 dataclass。
4. 遊戲計算邏輯 function。

可以較寬鬆的地方：

1. Streamlit UI callback。
2. 第三方 API 原始回應。
3. 圖表資料轉換的中間 DataFrame。

### 13.2 執行指令

```bash
mypy .
```

或：

```bash
bash scripts/type_check.sh
```

Windows PowerShell 可直接使用：

```powershell
mypy .
```

### 13.3 mypy 採用策略

第一階段：

1. 先讓 `services/` 和 `models/` 通過。
2. `ignore_missing_imports = true` 避免第三方套件阻塞。

第二階段：

1. 補齊 `database/` 型別。
2. 減少 `Any`。

第三階段：

1. 視時間提高嚴格程度。
2. 讓所有核心邏輯不依賴隱性型別。

## 14. 開發里程碑

### 14.1 Milestone 1：專案骨架與資料庫

目標：

1. 建立資料夾結構。
2. 建立 `app.py` 與 sidebar 導航。
3. 建立 SQLite schema。
4. 建立 `init_db()`。
5. 建立 seed data。

完成標準：

1. `streamlit run app.py` 可以打開首頁。
2. SQLite 資料表可以建立。
3. seed data function 可以被 import。

### 14.2 Milestone 2：資料查詢與球員百科

目標：

1. 建立 `nba_api_service.py`。
2. 建立 API fallback。
3. 建立球員搜尋。
4. 建立球員數據圖表。

完成標準：

1. API 正常時顯示真實資料。
2. API 失敗時顯示 seed data。
3. 頁面不因網路錯誤 crash。

### 14.3 Milestone 3：投票系統

目標：

1. 建立 polls、poll_options、votes 資料表。
2. 建立 `vote_service.py`。
3. 建立投票 UI。
4. 顯示統計結果。

完成標準：

1. 使用者可投票。
2. 同一投票不能重複投。
3. 統計數字正確。

### 14.4 Milestone 4：Fantasy Team 與 Matchup Debate

目標：

1. 建立 fantasy team 選人流程。
2. 建立簡易 fantasy score。
3. 建立 matchup 比較。
4. 建立 matchup 投票。

完成標準：

1. 使用者可以選 5 名球員。
2. 系統可以顯示隊伍總分。
3. Matchup Debate 可以投票並顯示結果。

### 14.5 Milestone 5：測試、型別、Demo 整理

目標：

1. 補 pytest。
2. 補 mypy 設定。
3. 整理 README。
4. 準備 demo script。
5. 整理 MVP 之後的功能缺口與改善優先順序。
6. 加入 `NBA_DATA_MODE=auto|seed`，讓 demo 可手動切換 API 與 seed data。

完成標準：

1. `pytest` 通過。
2. `mypy .` 無核心錯誤。
3. demo 時可切換 API 與 seed data。
4. README 有清楚的本機 demo 流程。
5. `DEVELOPMENT_SPEC.md` 有明確列出後續改善路線。
6. `python scripts/demo_check.py` 可快速驗證 demo 所需核心功能。

Milestone 5 建議輸出：

1. `scripts/demo_check.py`
2. `scripts/run_tests.ps1`
3. `scripts/type_check.ps1`
4. `scripts/demo_check.ps1`
5. README 的 setup、run、test、type check、demo check 說明。
6. `NBA_DATA_MODE` 環境變數：
   - `auto`：優先使用 NBA API，失敗時 fallback seed data。
   - `seed`：強制使用 seed data，適合教室網路不穩時展示。

### 14.6 Milestone 6：球員百科資料完整性與視覺化改善

目前問題：

1. 只有 Stephen Curry、LeBron James 等 seed data 內的大牌球員有完整得分、籃板、助攻、隊伍、位置。
2. 透過 `nba_api.stats.static.players` 搜到的其他球員只有基本姓名與 id，缺少即時 profile 與近年 per-game 數據。
3. 現有圖表只顯示簡單折線與表格，使用者不容易理解球員狀態。

目標：

1. 搜尋任一 NBA 球員後，盡量補齊隊伍、位置、近年得分、籃板、助攻。
2. 將 `PlayerCareerStats` 的總量數據轉成 per-game 數據，例如 `PTS / GP`、`REB / GP`、`AST / GP`。
3. 若 API 沒有位置或隊伍資料，使用最近一季 career stats 的 `TEAM_ABBREVIATION` 補隊伍，位置則顯示 `N/A` 並在 UI 標示「資料不足」。
4. 改善圖表呈現，至少提供：
   - 近年 PPG 折線圖。
   - RPG / APG 分組長條圖。
   - 最近一季重點指標卡。
   - 原始數據表格，可排序與篩選。
5. 將資料來源狀態顯示清楚：`api`、`seed`、`partial_api`。

建議實作：

1. 在 `services/nba_api_service.py` 新增或強化：
   - `get_player_career_stats(player_id: int)`
   - `get_player_latest_season_summary(player_id: int)`
   - `get_player_common_info(player_id: int)`，若 endpoint 不穩則 optional。
2. 在 `services/player_service.py` 新增：
   - `enrich_player_profile(player_id: int)`
   - `get_player_per_game_stats(player_id: int)`
   - `get_player_data_quality(player_id: int)`
3. 建立快取策略：
   - Streamlit 可使用 `st.cache_data(ttl=3600)`。
   - 或將 API 回來的球員 summary 寫入 SQLite cache table。
4. seed data 擴充到至少 30 名球員，涵蓋不同位置與球隊。

完成標準：

1. 搜尋非 seed 明星球員時，不會只看到 0 分、0 籃板、0 助攻。
2. 至少 20 名球員能顯示近年 per-game 數據。
3. UI 能清楚顯示資料是完整 API、部分 API 還是 fallback seed。
4. 圖表可讀性明顯提升，demo 時不需要解釋資料欄位代表什麼。

### 14.7 Milestone 7：雲端投票與多人 Demo 可行性

目前問題：

1. 若專案只在本機執行，SQLite database 只存在本機。
2. demo 現場若只有一台電腦投票，投票統計永遠接近單人使用情境。
3. Streamlit 本機版不適合展示「多人同時投票」的社群感。

決策方向：

MVP 可繼續保留 SQLite，因為課程專案限制優先使用 SQLite。但若要展示多人投票，必須新增雲端執行方案。

雲端選項：

| 方案 | 優點 | 缺點 | 建議用途 |
| --- | --- | --- | --- |
| Streamlit Community Cloud + SQLite | 最容易部署 | SQLite 持久化與多人寫入有限制 | 只適合展示 UI，不適合正式多人投票 |
| Render / Railway + SQLite persistent disk | 架構變動小 | 免費方案限制較多 | 小組 demo 可行 |
| Streamlit Community Cloud + Supabase Postgres | 多人投票穩定 | 需要多學一個雲端資料庫 | 最適合展示多人互動 |
| 本機區網分享 | 不需雲端帳號 | 同網路限制，穩定性看教室網路 | 備用方案 |

建議路線：

1. 短期：保留 SQLite，支援本機 demo。
2. 中期：抽象 `database/db.py`，保留 SQLite 介面，但讓 vote service 可切換 database backend。
3. Demo 強化版：使用 Supabase Postgres 或 Render persistent SQLite，讓同學用手機連同一個網址投票。

建議實作：

1. 新增環境變數：
   - `DATABASE_URL`
   - `APP_MODE=local|cloud`
2. 若 `DATABASE_URL` 未設定，使用 SQLite。
3. 若 `DATABASE_URL` 設定為 Postgres，使用 SQLAlchemy 或 psycopg 連線。
4. README 新增 cloud demo 流程。
5. 投票頁顯示目前模式：
   - 本機模式：`Local demo mode`
   - 雲端模式：`Cloud voting mode`

Milestone 7 實作輸出：

1. `config/settings.py`：集中管理 `APP_MODE`、`DATABASE_URL` 與 runtime 狀態。
2. `database/db.py`：支援 `DATABASE_URL=sqlite:///...` 指定 SQLite 路徑。
3. `pages/voting.py`：顯示 Local demo mode / Cloud voting mode 與資料庫提示。
4. `docs/CLOUD_DEPLOYMENT.md`：記錄本機區網、persistent SQLite、Supabase/Postgres 後續路線。
5. `.env.example`：提供 demo 用環境變數範例。

完成標準：

1. 本機 SQLite 投票仍可正常運作。
2. 至少有一份可部署到雲端的說明。
3. 若時間足夠，完成一個公開 demo URL，讓多台裝置可以同時投票。
4. 投票統計在多人投票後可以即時更新。

### 14.8 Milestone 8：Fantasy Team 球員池擴充與規則化

目前問題：

1. Fantasy Team 目前只能選 seed data 裡的少數球員，實際約 7 名。
2. 使用者很快就會覺得選擇不足。
3. 目前沒有位置限制、薪資限制或球員搜尋，玩法偏展示用。

目標：

1. 球員池至少擴充到 30 至 50 名。
2. 支援依球員姓名、球隊、位置篩選。
3. 建立清楚規則，讓 Fantasy Team 不只是任意選 5 人。

建議規則：

1. 必須選 5 名球員。
2. 建議位置組成：
   - 2 名 Guard
   - 2 名 Forward
   - 1 名 Center
3. 若位置資料不足，先使用寬鬆規則：最多 3 名同位置球員。
4. 進階版可加入 salary cap：
   - 每名球員依 fantasy score 給定 salary。
   - 使用者總 salary 不可超過 100。

建議實作：

1. `database/seed_data.py` 擴充球員資料。
2. `player_service` 新增 `get_player_pool()`。
3. `fantasy_team.py` 新增：
   - 搜尋框。
   - 球隊 filter。
   - 位置 filter。
   - 已選球員清單。
   - 規則檢查提示。
4. `game_service.py` 新增：
   - `validate_fantasy_roster(players)`
   - `calculate_player_salary(player)`
   - `calculate_total_salary(players)`

完成標準：

1. 使用者至少能從 30 名球員中選 5 人。
2. UI 能顯示每名球員的 fantasy score 與 salary。
3. 若違反規則，系統會清楚提示原因。
4. Fantasy Team 頁面適合重複操作，不需要重新整理才能看懂狀態。

### 14.9 Milestone 9：Matchup Debate 定位重整

目前問題：

1. 目前兩隊都只有 3 名球員，使用者不清楚這是 3v3、5v5 還是單純人氣投票。
2. 模型計算規則沒有清楚呈現，容易讓使用者覺得結果是黑箱。
3. 功能定位不明確：到底是 debate、模擬器，還是投票頁。

重新定位：

Matchup Debate 應定位為「5v5 陣容辯論與簡易模型模擬」。它不是準確預測比賽結果，而是讓球迷比較兩組陣容的數據特性，並投票表達支持方。

功能規則：

1. 每個 matchup 預設為 5v5。
2. 頁面必須清楚顯示兩種結果：
   - 模型結果：依數據公式計算。
   - 球迷投票：依使用者投票計算。
3. 模型公式需在頁面用可展開區塊顯示：

```text
team_power =
  avg_points * 0.4
  + avg_rebounds * 0.2
  + avg_assists * 0.2
  + defense_score * 0.2

defense_score = avg_steals * 2 + avg_blocks * 2
```

4. 頁面文案需說明：這是課程專案用的簡化模型，不代表真實 NBA 勝率。

建議實作：

1. seed matchup 改為 5v5，例如：
   - Spurs Inspired Young Core vs NBA Superstars。
   - Old School Legends vs Modern Stars。
2. `game_service.py` 新增：
   - `validate_matchup_lineup(team_a, team_b)`
   - `get_matchup_explanation()`
3. `matchup_debate.py` 新增：
   - 模型規則展開區。
   - 球員數據比較表。
   - 模型結果與球迷投票分開顯示。
   - 自訂 matchup 的輸入流程，若時間足夠。

完成標準：

1. 每隊至少 5 名球員。
2. 使用者能理解模型公式。
3. 頁面能同時展示「模型看好誰」與「球迷支持誰」。
4. 功能名稱、文案、互動流程一致，不再讓使用者困惑。

### 14.10 Milestone 10：Spurs 風格前端與整體 UI Polish

目前問題：

1. Streamlit 預設元件視覺較簡單，頁面看起來像功能測試工具。
2. 首頁與各功能頁缺少一致的視覺語言。
3. 使用者是馬刺迷，可以將設計方向做得更有個性。

設計方向：

採用 San Antonio Spurs inspired 的黑、銀、白視覺風格，但不要直接使用未授權官方 logo 或受版權保護素材。可使用幾何線條、銀色金屬感、球場線條、低調黑白對比建立風格。

建議視覺規範：

1. 主色：
   - 黑色：`#0B0B0C`
   - 銀色：`#C4CED4`
   - 白色：`#F8F8F8`
   - 深灰：`#1D1F21`
2. 輔助色：
   - 冷藍灰：`#7E8A97`
   - 成功綠：`#2E7D5B`
   - 警示紅：`#B94A48`
3. 字體：
   - 保持系統字體，避免外部字體載入失敗。
4. Layout：
   - 使用清楚的 section header。
   - 減少過長表格直接鋪滿。
   - 指標卡使用一致樣式。
   - 圖表旁保留簡短註解。

建議實作：

1. 新增 `.streamlit/config.toml`：
   - 設定 base theme。
   - 設定 primary color、background、text color。
2. 新增 `styles/` 或 `ui/` helper：
   - `ui/theme.py`
   - `ui/components.py`
3. 建立共用元件：
   - `render_page_header(title, subtitle)`
   - `render_source_badge(source)`
   - `render_metric_row(metrics)`
   - `render_section(title)`
4. 優先美化頁面：
   - 首頁。
   - 球員百科。
   - Fantasy Team。
   - Matchup Debate。
5. 可加入 Spurs-inspired hero，不使用官方 logo：
   - 黑銀背景。
   - 球場線條。
   - NBA FANS TAIWAN 字樣。

完成標準：

1. 所有頁面視覺一致。
2. 首頁第一眼能看出這是 NBA 球迷平台，不像單純資料表工具。
3. 球員百科、Fantasy Team、Matchup Debate 的資訊層次清楚。
4. 手機寬度下文字與圖表不重疊。
5. 不使用未授權官方 logo 或侵權圖片。

### 14.11 Milestone 5 之後的建議優先順序

若剩餘時間有限，建議優先順序如下：

1. 先做 Milestone 6，因為球員百科是資料平台核心，資料不完整會直接影響 demo 說服力。
2. 再做 Milestone 9，因為 Matchup Debate 目前定位最不清楚，需要先補規則與 5v5 架構。
3. 接著做 Milestone 8，擴充 Fantasy Team 球員池，讓互動性更好。
4. 若課程展示需要多人參與，再做 Milestone 7 的雲端投票。
5. 最後做 Milestone 10 的 UI polish；若展示重視第一印象，則可把 Milestone 10 提前與 Milestone 6 同步進行。

### 14.12 Milestone 11：Spurs-inspired Dark Dashboard 前端優化

目前問題：

1. Milestone 10 已建立基本黑銀風格與共用元件，但頁面仍大量依賴 Streamlit 預設表單式排版，視覺仍像「資料表工具」。
2. 圖表使用 `st.line_chart`、`st.bar_chart`，色彩與字型無法配合 Spurs 風格，圖表標籤偏淺、與深色背景對比不足。
3. 指標卡、球員清單、Matchup 比較等核心區塊缺少卡片化、層次與資訊密度設計，第一眼看不出資訊重點。
4. Fantasy Team 球員池與 Matchup Debate 兩隊比較資訊量大，但目前仍以 dataframe 直接鋪滿，難以聚焦。

目標：

針對前端 UI 進行優化，**不要使用 Streamlit 預設表單式排版**。請使用 custom CSS、columns、cards、tabs、metrics、Plotly charts，做出 Spurs-inspired dark dashboard。

設計方向：

1. 全站視覺以 dashboard 為核心：hero、KPI strip、card grid、chart panel 為主要區塊型態。
2. 沿用 Milestone 10 的黑、銀、白、深灰色票，新增以下輔助：
   - 圖表線條主色：銀色 `#C4CED4`
   - 圖表對比色：冷藍灰 `#7E8A97`、警示紅 `#B94A48`、成功綠 `#2E7D5B`
   - 卡片背景：`#131416`，邊框 `#2A2C2F`
3. 字級層次：hero 標題 `2rem`、section 標題 `1.15rem`、KPI 數字 `1.6rem`、輔助文字 `0.85rem`。
4. 所有圖表改用 Plotly，並統一套用 dark template，無多餘格線、tooltip 與背景色透明。
5. 互動元件（按鈕、tab、selectbox）視覺與 Milestone 10 sidebar 一致：silver border、hover 微亮、selected 加粗。

建議實作：

1. 依賴更新：
   - `requirements.txt` 加入 `plotly`。
2. 新增共用元件（`ui/components.py` 擴充或新檔）：
   - `render_stat_card(label, value, sub, accent)`：自訂卡片，取代部分 `st.metric` 方塊感。
   - `render_player_card(player, fantasy_score, salary)`：球員卡，含隊伍 chip、PTS/REB/AST 小數據條，無頭像時用首字母 avatar。
   - `render_kpi_strip(items)`：hero 下方橫向 KPI 列。
   - `render_progress_ring(pct, label)`：純 CSS conic-gradient 圓環，取代 ASCII salary bar。
   - `render_vs_block(team_a, team_b, win_a, win_b)`：Matchup 大字 VS 區塊。
3. 新增圖表模組 `ui/charts.py`：
   - `player_trend_chart(df, metrics)`：Plotly 折線圖（PPG / RPG / APG 多線）。
   - `player_radar_chart(player)`：雷達圖（得分、籃板、助攻、抄截、火鍋）。
   - `team_compare_bar(team_a, team_b, labels)`：兩隊水平 bar 對比。
   - `vote_donut_chart(summary)`：投票結果 donut 圖。
   - 所有圖表共用 `plotly_dark_layout()` helper，背景透明、字體銀色、無格線。
4. CSS 擴充（`ui/theme.py`）：
   - `.spurs-card`、`.spurs-card-hover`：基本卡片樣式。
   - `.spurs-player-card`：球員卡（avatar + 隊伍 chip + stats grid）。
   - `.spurs-kpi-strip`：KPI 橫條。
   - `.spurs-ring`：純 CSS 圓環。
   - `.spurs-vs`：Matchup 大字 VS 區塊。
   - 隱藏 Streamlit 預設 `st.metric` 的方塊邊框、調暗 input 邊框。
5. 頁面改寫範圍：
   - `home.py`：hero + KPI strip（球員 / 投票 / Matchup 數量）+ 三張 feature card + 今日焦點改球員卡。
   - `realtime_hub.py`：賽程改 card 列表（home vs away 大比分），不再用 dataframe 鋪滿。
   - `player_stats.py`：KPI strip + Plotly 折線 + 雷達圖 + 數據表 tab。
   - `fantasy_team.py`：球員池改卡片格（3 欄 grid 或保留表格與卡片並行）+ Plotly donut + 圓環 salary。
   - `matchup_debate.py`：VS block + 兩隊 Plotly bar 對比 + 投票 donut。
   - `voting.py`：每個 poll 改卡片，結果改 Plotly donut。

實作風險與取捨：

1. Plotly 為新依賴，需更新 `requirements.txt` 並提示組員 `pip install -r requirements.txt`。
2. `Player.image_url` 多為 None，球員卡需以首字母 avatar 取代，避免抓外部圖造成破版與版權風險。
3. 球員池 30+ 名球員若全部改卡片格會太擠，建議「卡片格 + 表格切換」或保留表格搭配 column config 強化。
4. 自訂 CSS 必須每次 rerun 注入（已於 Milestone 10 修正 `inject_global_styles`），新增的 component HTML 同樣不可仰賴 session state 快取。
5. Plotly 圖表色票與 Milestone 10 sidebar、卡片色票一致，避免兩套設計語言。

完成標準：

1. 各頁面第一屏沒有任何 `st.dataframe` 鋪滿、無樣式的 form 排版。
2. 至少 4 種圖表類型以 Plotly 呈現（折線、雷達、水平 bar、donut）。
3. 球員、賽程、Matchup、投票皆有卡片化呈現，資訊層次清楚。
4. 全站視覺語言一致：hero、card、KPI、chart 色票與字體統一。
5. 手機寬度下卡片自動換行、圖表不溢出。
6. `pytest` 與 `python scripts/demo_check.py` 仍維持通過。

## 15. 組員分工建議

| 角色 | 負責範圍 | 主要檔案 |
| --- | --- | --- |
| UI 組 | Streamlit 頁面、sidebar、圖表 | `app.py`, `pages/` |
| NBA 資料組 | `nba_api` 串接、fallback、資料整理 | `services/nba_api_service.py`, `services/player_service.py` |
| 資料庫組 | SQLite schema、CRUD、seed data | `database/` |
| 互動功能組 | 投票、Fantasy Team、Matchup Debate | `vote_service.py`, `game_service.py`, 對應 pages |
| 測試與整合組 | pytest、mypy、README、demo 流程 | `tests/`, `pyproject.toml`, `README.md` |

若人數較少，可以合併成三組：

1. UI 與頁面組。
2. 資料與資料庫組。
3. 遊戲互動與測試組。

## 16. 現有原型遷移建議

目前專案已有早期原型檔案，例如：

1. `nba_main.py`
2. `init_db.py`
3. `nba.py`
4. `first.py`

建議不要一開始直接刪除，而是採用漸進式遷移：

1. 先建立新結構。
2. 將 `nba_main.py` 中的 Player、Matchup 類別搬到 `models/`。
3. 將使用者與投票資料庫 function 搬到 `database/db.py` 與 `services/vote_service.py`。
4. 將 Streamlit 畫面拆到 `pages/`。
5. 確認新 `app.py` 可執行後，再將舊檔標記為 legacy 或移到 `legacy/`。

遷移時要特別處理：

1. 目前部分檔案可能有文字編碼亂碼。
2. 密碼不應明文儲存。
3. SQL 操作應集中管理。
4. 頁面文案應統一使用繁體中文。

## 17. Demo 風險控管

### 17.1 Demo 前檢查清單

1. 確認 `streamlit run app.py` 可以啟動。
2. 確認 SQLite database 可建立。
3. 確認每個頁面都能開啟。
4. 關閉網路後確認 seed data 可展示。
5. 確認投票可以寫入資料庫。
6. 確認 Fantasy Team 可以選人並計分。
7. 確認 Matchup Debate 可以投票並顯示比例。
8. 確認 `pytest` 通過。
9. 確認 `mypy .` 至少核心模組通過。

### 17.2 Demo 資料策略

建議 demo 時準備固定資料：

1. Lakers vs Warriors 比賽範例。
2. Stephen Curry、LeBron James、Nikola Jokic、Luka Doncic、Giannis Antetokounmpo 等球員範例。
3. MVP 預測投票。
4. 總冠軍預測投票。
5. 經典 matchup，例如 Team Old School vs Team New Generation。

固定 demo data 可確保展示流程穩定，不受當天 NBA 賽程影響。

## 18. 程式品質規範

### 18.1 命名

1. Python 檔案與 function 使用 snake_case。
2. class 使用 PascalCase。
3. 常數使用 UPPER_SNAKE_CASE。
4. UI 顯示文字使用繁體中文。
5. 內部變數建議使用英文，避免編碼問題。

### 18.2 錯誤處理

1. API 呼叫必須 try/except。
2. 資料庫連線必須確實 close。
3. 使用者輸入要檢查空字串。
4. 投票重複時要給清楚提示。
5. 遊戲邏輯遇到空隊伍時要回傳合理錯誤。

### 18.3 不建議做法

1. 不要在 Streamlit page 內直接寫大量 SQL。
2. 不要把所有邏輯都寫在 `app.py`。
3. 不要讓 UI 直接依賴 `nba_api` 的原始格式。
4. 不要在測試中呼叫真實 NBA API。
5. 不要將 demo 成敗綁定在即時網路連線。

## 19. 建議實作順序

建議照以下順序開發：

1. 建立資料夾結構與空檔案。
2. 建立 `database/schema.sql`。
3. 建立 `database/db.py` 與 `init_db()`。
4. 建立 `database/seed_data.py`。
5. 建立 `models/player.py`、`models/team.py`、`models/matchup.py`。
6. 建立 `services/nba_api_service.py` fallback 版本。
7. 建立 `pages/home.py` 與 `pages/realtime_hub.py`。
8. 建立 `player_service.py` 與 `pages/player_stats.py`。
9. 建立 `vote_service.py` 與 `pages/voting.py`。
10. 建立 `game_service.py`、Fantasy Team、Matchup Debate。
11. 補 pytest。
12. 補 mypy。
13. 整理 README 與 demo script。

## 20. 驗收標準

MVP 可被視為完成，需符合：

1. 使用者可以透過 Streamlit sidebar 切換所有頁面。
2. 即使沒有外部網路，核心頁面仍可展示 seed data。
3. 球員搜尋與圖表至少能展示一組資料。
4. 投票可以寫入 SQLite 並統計。
5. Fantasy Team 可以選球員並計分。
6. Matchup Debate 可以比較兩隊並投票。
7. 專案有基本測試。
8. 專案有 mypy 設定。
9. README 說明如何安裝、啟動、測試。
10. 程式結構清楚，UI、service、database 沒有全部混在同一檔案。

## 21. 最小可展示版本定義

如果時間不足，最低限度應完成：

1. `app.py` 可啟動。
2. `home.py`、`player_stats.py`、`voting.py`、`matchup_debate.py` 可展示。
3. 使用 seed data 也能完成所有 demo。
4. 投票資料真的寫入 SQLite。
5. 至少有 4 個 pytest 測試：
   - fantasy score 計算
   - matchup winner 判斷
   - 投票寫入
   - 重複投票限制

這樣即使 `nba_api` 來不及完整串接，仍然可以展示完整互動流程。
