# Cloud Voting Deployment Notes

Milestone 7 keeps SQLite as the working database because the course project prioritizes SQLite, but adds deployment mode visibility and environment settings for demo planning.

## Modes

| Variable | Value | Behavior |
| --- | --- | --- |
| `APP_MODE` | `local` | Local classroom/demo mode. Voting data stays in the current machine/runtime. |
| `APP_MODE` | `cloud` | Cloud demo mode. UI labels voting as shared if a cloud-capable database setting is present. |
| `NBA_DATA_MODE` | `auto` | Use NBA API first, fallback to seed data. |
| `NBA_DATA_MODE` | `seed` | Force seed data for stable demos. |
| `DATABASE_URL` | empty | Use default local SQLite file. |
| `DATABASE_URL` | `sqlite:///data/nba_fans_taiwan.db` | Use a specific SQLite path. In cloud, this needs persistent disk to survive restarts. |

## Recommended Demo Options

### Option A: Local Classroom Demo

Use this when one laptop presents the project.

```powershell
$env:APP_MODE = "local"
$env:NBA_DATA_MODE = "seed"
streamlit run app.py
```

Pros:
- Most stable.
- No cloud account needed.
- SQLite works exactly as implemented.

Cons:
- Voting is not truly multi-user unless everyone connects to the same local machine.

### Option B: Local Network Sharing

Use this if classmates are on the same Wi-Fi and can reach the presenter's laptop.

```powershell
$env:APP_MODE = "cloud"
$env:NBA_DATA_MODE = "seed"
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Then share:

```text
http://<presenter-local-ip>:8501
```

Pros:
- Minimal code and deployment work.
- Multiple devices can vote against the same local SQLite database.

Cons:
- Depends on classroom Wi-Fi and firewall settings.

### Option C: Cloud VM or Render/Railway with Persistent SQLite

Set:

```text
APP_MODE=cloud
NBA_DATA_MODE=auto
DATABASE_URL=sqlite:///data/nba_fans_taiwan.db
```

Requirements:
- The `data/` directory must be on persistent storage.
- If the platform resets the filesystem on each deploy, votes will be lost.

Pros:
- Public URL is possible.
- Minimal code changes.

Cons:
- SQLite concurrent writes are limited.
- Persistent disk setup depends on hosting platform.

### Option D: Supabase Postgres

This is the best long-term multi-user voting option, but it is not implemented in the current code path.

Planned setting:

```text
APP_MODE=cloud
DATABASE_URL=postgresql://...
```

Current behavior:
- The app detects Postgres intent and shows cloud voting status.
- Vote persistence still uses SQLite helpers until a Postgres backend is implemented.

Next implementation step:
- Introduce a database adapter interface.
- Add a Postgres implementation for `polls`, `poll_options`, `votes`, and `matchup_votes`.
- Keep SQLite as the default local backend.

## Demo Checklist

Before presenting:

```powershell
python scripts/demo_check.py
pytest
mypy .
```

For safest classroom demo:

```powershell
$env:APP_MODE = "local"
$env:NBA_DATA_MODE = "seed"
streamlit run app.py
```
