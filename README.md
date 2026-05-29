# NBA FANS TAIWAN

Python + Streamlit + SQLite course project for an interactive NBA fan platform.

## Current Status

Milestone 10 is implemented:

- Streamlit app shell with sidebar navigation
- Layered project structure
- SQLite schema and initialization helper
- Seed data for offline demo safety
- NBA API service with automatic seed-data fallback
- Player search and player stats visualization page
- Per-game player stats, profile enrichment, and data quality indicators
- SQLite voting system with duplicate-vote prevention
- Fantasy Team selection, scoring, and persistence (30+ player pool, salary cap, position rules)
- Matchup Debate simulation and voting (5v5, model vs fan vote)
- Basic pytest and mypy configuration
- Demo check script
- API/seed data mode switch for stable demos
- App/database mode detection for local vs cloud voting demos
- Spurs-inspired dark theme (black / silver / white) via `.streamlit/config.toml`
- Shared UI components (`ui/theme.py`, `ui/components.py`): hero header, section titles, source badges

## Setup

```powershell
C:\Users\maurice\AppData\Local\Programs\Python\Python312\python.exe -m pip install -r requirements.txt
```

## Run

Use live NBA API when available, with automatic fallback to seed data:

輸入以下指令即可:
```powershell
streamlit run app.py
```

Force offline seed data mode for a stable classroom demo:

```powershell
$env:NBA_DATA_MODE = "seed"
streamlit run app.py
```

Return to automatic API mode:

```powershell
$env:NBA_DATA_MODE = "auto"
streamlit run app.py
```

## Test

```powershell
pytest
```

or:

```powershell
.\scripts\run_tests.ps1
```

## Type Check

```powershell
mypy .
```

or:

```powershell
.\scripts\type_check.ps1
```

## Demo Check

Run this before presenting. It verifies SQLite tables, seed mode, voting, Fantasy Team, and Matchup Debate logic:

```powershell
python scripts/demo_check.py
```

or:

```powershell
.\scripts\demo_check.ps1
```

Expected output:

```text
demo check passed
```

## 先知幣預測系統（Prophet Coin）

### 功能概覽

| 功能 | 說明 |
|---|---|
| **即時預測** | 季後賽每輪開打前開放「晉級隊伍預測」，第一場開打後自動鎖定，系列賽結束自動結算 |
| **長期預測** | 賽季初開放年度獎項預測（MVP / 總冠軍 / DPOY / ROY / 最佳第六人 / MIP / FMVP） |
| **先知幣** | 正確預測可獲得先知幣，越早押注、幣數越多（指數衰減公式） |
| **排行榜** | 全體預測者依先知幣總數排名 |

### 先知幣計算公式

```
先知幣 = base × exp( −4 × t )

t = (最後更改時間 − 項目開放時間) / (結算時間 − 項目開放時間)   ∈ [0, 1]
```

| 預測類型 | base 上限 | 範例：t=0（最早） | t=0.5（中段） | t=0.9（接近結算） |
|---|---|---|---|---|
| 長期獎項（365 天窗口） | 1000 | 1000 幣 | 135 幣 | 27 幣 |
| 即時系列賽（約 10 天窗口） | 200 | 200 幣 | 27 幣 | 5 幣 |

規則：
- 預測錯誤 **不扣分**
- 可隨時更改預測，但計分以**最後一次更改**的時間為準
- 即時預測項目在系列賽**第一場開打**後自動鎖定（不可再更改）

### 即時預測——運作流程

```
上一輪所有系列賽結束
      ↓
系統自動建立下一輪各系列賽的預測項目（status = open）
      ↓
使用者在任意時間押注哪隊晉級
      ↓
某系列賽 G1 開打（wins_a + wins_b > 0）→ 自動鎖定（status = locked）
      ↓
系列賽結束（winner 確定）→ 自動結算先知幣（status = settled）
```

第一輪預測在偵測到 `SeasonPhase = PLAYOFFS` 時立即開放（不需要等「上一輪」）。

### 長期預測——運作流程

```
app 初始化時自動建立 7 個獎項預測項目（每賽季執行一次，冪等）
      ↓
使用者隨時押注（球員搜尋欄 / 隊伍下拉選單）
      ↓
獎項官方公布後，管理員在頁面底部結算區塊輸入正確答案
      ↓
系統比對所有使用者的最後預測，計算並發放先知幣
```

### 長期獎項項目（7 項）

| key | 中文標籤 | 選項類型 |
|---|---|---|
| `{season}_mvp` | 年度 MVP | 球員搜尋 |
| `{season}_champion` | 總冠軍 | 30 隊下拉 |
| `{season}_dpoy` | 最佳防守球員 | 球員搜尋 |
| `{season}_roy` | 最佳新秀 | 球員搜尋 |
| `{season}_sixth_man` | 最佳第六人 | 球員搜尋 |
| `{season}_mip` | 最佳進步獎 | 球員搜尋 |
| `{season}_fmvp` | 總決賽 MVP | 球員搜尋 |

### 管理員結算操作

1. 進入「先知幣預測」頁面，捲到最底部
2. 展開「管理員結算（長期獎項）」區塊
3. 輸入管理員密碼（預設 `admin`；正式部署請設定環境變數 `PROPHET_ADMIN_PASSWORD`）
4. 對每個尚未結算的獎項輸入正確答案，按「結算」按鈕
5. 系統自動比對所有使用者預測並發放先知幣

正確答案**不分大小寫**（`shai gilgeous-alexander` = `Shai Gilgeous-Alexander`）。

### 環境變數

| 變數 | 預設值 | 說明 |
|---|---|---|
| `PROPHET_ADMIN_PASSWORD` | `admin` | 管理員結算頁面的密碼，部署前請務必修改 |

### 資料庫結構（新增 4 張表）

| 表 | 說明 |
|---|---|
| `prophet_users` | 使用者暱稱與先知幣總數 |
| `prediction_items` | 預測項目目錄（open / locked / settled） |
| `user_predictions` | 每位使用者的每筆預測紀錄 |
| `settlement_events` | 正確答案與結算時間 |

表格由 `init_db()` 在 app 啟動時自動建立，現有資料庫升級時不需要手動執行 migration。

---

## Demo Notes

- `APP_MODE=local`: local classroom mode.
- `APP_MODE=cloud`: cloud/shared voting demo mode.
- `NBA_DATA_MODE=auto`: use NBA API when possible, fallback to seed data on API/network errors.
- `NBA_DATA_MODE=seed`: always use local seed data. This is recommended for classroom demos when network reliability is uncertain.
- `DATABASE_URL=sqlite:///data/nba_fans_taiwan.db`: use a specific SQLite path. Cloud hosts need persistent disk for vote persistence.
- Local SQLite data is stored under `data/` and is ignored by Git.

## Cloud Voting

See [docs/CLOUD_DEPLOYMENT.md](docs/CLOUD_DEPLOYMENT.md) for local network sharing, persistent SQLite hosting, and future Supabase/Postgres notes.

## Project Spec

See [DEVELOPMENT_SPEC.md](DEVELOPMENT_SPEC.md) for milestones, architecture, data model, and team responsibilities.
