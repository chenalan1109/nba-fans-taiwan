# NBA FANS TAIWAN — 改版紀錄

## v2.1.0 — 2026-05-30（UI 美化）

本次更新由 Claude Code 執行，涵蓋首頁比賽狀況排版改進、Matchup Debate 管理員模式位置調整、選單提示文字新增，共計修改 2 個檔案。

### 1. 首頁「比賽狀況」排版調整（`_pages/home.py`）

**改動說明：**
- `_render_bracket()` 函數拆出 `_render_round_content()` 輔助函數，將每輪內容的渲染邏輯獨立。
- 新增 `_is_round_active()` 內部函數：若某輪中任一系列賽 `status != "finished"`，則判定該輪「進行中」。
- 渲染順序改為：進行中的輪次不加任何折疊、直接顯示在最上方；已結束的輪次以 `st.expander` 收起，按鈕名稱為「查看第{輪次數字}輪比賽結果」。
- 同一類型（進行中 / 已結束）的多輪，以輪次數字由高到低排列（例如第三輪在第二輪之前）。

**影響的資料流：**
- 資料來源 `get_playoff_series()` 回傳結構不變，只改渲染層邏輯。
- 若目前為季後賽且所有輪次均已結束，所有輪次都會以 expander 呈現。

---

### 2. Matchup Debate 管理員模式移到頁面最下方（`_pages/matchup_debate.py`）

**改動說明：**
- 原本「🔑 管理員模式」expander 位於「建立自訂對決」expander 正下方（頁面第二個區塊）。
- 現在移到 `render()` 函數末尾，在所有對決內容（陣容卡、數據對比、球迷投票 tabs）之後，並加上 `st.divider()` 分隔線。
- 功能不變，`_render_admin_panel(custom_matchup_list)` 呼叫及 `custom_matchup_list` 變數不受影響。

---

### 3. Matchup Debate 選單加上提示文字（`_pages/matchup_debate.py`）

**改動說明：**
- 原本 `st.selectbox("選擇對決", titles, label_visibility="collapsed")` 使用 `label_visibility="collapsed"` 隱藏標籤。
- 改為 `st.selectbox("請選擇有興趣的對決組合", titles)`，顯示完整提示文字，引導用戶選擇對決組合。

---

## v2.0.0 — 2026-05-30

本次更新由 Claude Code 執行，涵蓋效能修正、帳號系統、Fantasy 球員市場、球員殿堂管理員功能，共計修改 9 個既有檔案、新增 3 個檔案。

---

### 1. 效能修正：球迷投票頁面慢速問題

**問題根因：**
- `ensure_tomorrow_game_polls()` 在每次頁面載入時呼叫 NBA API（`nba_api.stats.endpoints.scoreboardv2`），造成 3–10 秒延遲。
- `list_active_polls()` 對每個 Poll 分別查詢一次 `poll_options`（N+1 query 問題）。

**修正方式：**
- `services/vote_service.py`：新增 `_last_game_poll_refresh` 全域變數，讓 `ensure_tomorrow_game_polls` 最多每 60 分鐘執行一次，其餘直接 return。
- `services/vote_service.py`：`list_active_polls()` 改為單一 JOIN 查詢，一次取得所有 active polls 及其 options，消除 N+1 問題。
- `services/vote_service.py`：新增 `get_total_active_votes()` 函數，使用單一 COUNT 查詢取得總票數，取代舊版對每個 poll 分別呼叫 `get_vote_summary()` 的迴圈。

---

### 2. 帳號密碼系統

**取代原本「輸入暱稱即可投票」的匿名機制。**

**新增資料庫表：**
```sql
-- database/schema.sql + schema_pg.sql
CREATE TABLE user_accounts (
    id, username UNIQUE, password_hash, nickname, created_at
);
```

**新增服務：`services/auth_service.py`**
- `register_user(username, password, nickname)` — 驗證格式、檢查唯一性、SHA-256 雜湊密碼後寫入 `user_accounts`，同時在 `prophet_users` 建立初始 500 先知幣紀錄。
- `login_user(username, password)` — 驗證帳號密碼，回傳使用者 dict 或 None。
- `get_account(username)` — 查詢帳號資訊（不含密碼 hash）。
- `change_password(username, old_password, new_password)` — 驗證舊密碼後更新。

**登入後行為：**
- `st.session_state["logged_in_user"]` 存放登入用戶資訊 `{id, username, nickname}`。
- `st.session_state["voter_id"]` 自動設為該用戶的 `nickname`，與 prophet 先知幣系統相容。
- 帳號建立 → 自動獲得 500 先知幣（儲存在 `prophet_users.coins`）。

**頁面改動：`_pages/voting.py`**
- 移除原本的暱稱 `text_input`，改為登入/註冊表單（兩個 tab）。
- 未登入時只顯示公開 KPI（投票主題數、總票數），不顯示個人資料。
- 登入後顯示用戶資訊列（帳號、暱稱、先知幣）+ 登出按鈕。

**`app.py` sidebar：**
- 已登入時顯示帳號名稱、暱稱、先知幣餘額，以及登出按鈕。
- 未登入時顯示提示文字。

---

### 3. Fantasy Team 球員市場 + 球員池

**取代原本「從全體球員池直接組隊」的模式。**

**新增資料庫表：**
```sql
CREATE TABLE user_player_pool (
    id, username, player_id, player_name, purchased_at,
    UNIQUE (username, player_id)
);
```

**新增服務：`services/market_service.py`**
- `get_player_price(player)` — 定價演算法：`max(30, int(fantasy_score × 5))`。
  - 一般球員（fantasy_score ≈ 25）：≈ 125 先知幣
  - 明星球員（fantasy_score ≈ 45）：≈ 225 先知幣
  - 超級巨星（fantasy_score ≈ 65）：≈ 325 先知幣
  - 500 先知幣起始資金可購買約 2–3 名球員
- `buy_player(username, nickname, player)` — 扣除先知幣、寫入 `user_player_pool`。
- `get_user_player_pool_ids(username)` — 查詢用戶擁有的 player_id set。
- `has_player(username, player_id)` — 檢查是否已擁有該球員。
- `get_user_coins(nickname)` — 查詢先知幣餘額。

**`_pages/fantasy_team.py` 改版：**

頁面分為三個 tab：

**🛒 球員市場**
- 顯示所有可購買球員（支援姓名/球隊/位置篩選）。
- 每張球員卡下方顯示購買按鈕 + 價格（先知幣）。
- 已擁有的球員顯示「✓ 已擁有」。
- 先知幣不足時按鈕 disabled。

**🎒 我的球員池**
- 顯示用戶已購買的球員，含 Fantasy 分、市場價格。
- 支援卡片檢視和表格檢視兩種模式。

**🏀 組建 Fantasy Team**
- 只顯示球員池內的球員（非全體球員）。
- 其餘規則不變：5 人、位置上限 3 名、薪資模式。
- 未登入或球員池為空時顯示提示。

---

### 4. 球員殿堂管理員系統

**讓管理員可以從 UI 新增或停用投票主題，取代原本全部硬編碼在 `hall_service.py` 中的做法。**

**新增資料庫表：**
```sql
CREATE TABLE hall_poll_definitions (
    id, poll_key UNIQUE, title, subtitle,
    poll_type CHECK ('player','team','custom'),
    options_json, is_active, display_order, created_at
);
```

**`services/hall_service.py` 改版：**
- `get_hall_polls()` — 從 DB 讀取 active 的 poll definitions，首次呼叫時自動 seed 6 個預設主題（idempotent）。
- `create_hall_poll(poll_key, title, subtitle, type, options)` — 新增投票主題。
- `delete_hall_poll(poll_key)` — 軟刪除（設 `is_active=0`）。
- `restore_hall_poll(poll_key)` — 恢復已停用的主題。
- `list_all_hall_polls()` — 管理員用，列出所有（含停用）的主題。

**`_pages/voting.py` 球員殿堂 tab 新增管理員面板：**
- 使用 `PROPHET_ADMIN_PASSWORD` 環境變數（預設 `admin`）驗證。
- 可查看全部投票主題（含停用），並一鍵停用或恢復。
- 可透過表單新增新的投票主題（支援 player/team/custom 三種類型）。
- 管理員面板以 `st.expander` 收合，一般用戶不會誤觸。

---

### 異動檔案一覽

| 檔案 | 異動類型 | 說明 |
|---|---|---|
| `database/schema.sql` | 修改 | 新增 3 個表：`user_accounts`, `user_player_pool`, `hall_poll_definitions` |
| `database/schema_pg.sql` | 修改 | 同上（Postgres 版） |
| `database/db.py` | 修改 | `_run_migrations()` 新增對應的 SQLite + Postgres migration |
| `services/auth_service.py` | **新增** | 帳號系統：register/login/change_password |
| `services/market_service.py` | **新增** | 球員市場：定價/購買/查詢球員池 |
| `services/hall_service.py` | 重寫 | 改為 DB-backed poll definitions + admin CRUD |
| `services/vote_service.py` | 修改 | 效能修正（rate-limit game polls + N+1 fix + total votes query） |
| `_pages/voting.py` | 重寫 | 帳號登入 UI + 球員殿堂管理員面板 |
| `_pages/fantasy_team.py` | 重寫 | 三分頁市場/球員池/組隊架構 |
| `app.py` | 修改 | Sidebar 顯示登入狀態 + 登出按鈕 |
| `CHANGELOG.md` | **新增** | 本文件 |

---

### 注意事項（部署）

1. **舊資料庫相容**：`_run_migrations()` 會自動在現有 DB 新增三個表，不影響既有資料。
2. **舊帳號（prophet_users）**：舊的暱稱紀錄不受影響，但需重新建立帳號才能登入新系統。
3. **環境變數**：無新增環境變數；管理員密碼沿用 `PROPHET_ADMIN_PASSWORD`（預設 `admin`）。
4. **先知幣**：帳號建立時寫入 500 先知幣到 `prophet_users`；市場購買和預測系統共用同一個 `coins` 欄位。
