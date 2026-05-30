PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Full account system with password auth
CREATE TABLE IF NOT EXISTS user_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    nickname TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Player marketplace: each username owns a pool of purchased players
CREATE TABLE IF NOT EXISTS user_player_pool (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    player_name TEXT NOT NULL,
    purchased_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (username, player_id)
);

-- Hall of Fame poll definitions managed via DB (admin can add/remove)
CREATE TABLE IF NOT EXISTS hall_poll_definitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    poll_key TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    subtitle TEXT NOT NULL,
    poll_type TEXT NOT NULL CHECK (poll_type IN ('player', 'team', 'custom')),
    options_json TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    display_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS polls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    correct_answer TEXT,
    completed_at TEXT,
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

CREATE TABLE IF NOT EXISTS custom_matchups (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    team_a_name TEXT NOT NULL,
    team_b_name TEXT NOT NULL,
    team_a_players TEXT NOT NULL,
    team_b_players TEXT NOT NULL,
    creator_id TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS player_ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    voter_id TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (player_id, voter_id)
);

CREATE TABLE IF NOT EXISTS hall_votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    poll_key TEXT NOT NULL,
    voter_id TEXT NOT NULL,
    choice TEXT NOT NULL,
    voted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (poll_key, voter_id)
);

CREATE TABLE IF NOT EXISTS game_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL,
    voter_id TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS comment_likes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comment_id INTEGER NOT NULL,
    voter_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (comment_id, voter_id),
    FOREIGN KEY (comment_id) REFERENCES game_comments(id)
);

-- Prophet coin prediction system
CREATE TABLE IF NOT EXISTS prophet_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nickname TEXT UNIQUE NOT NULL,
    coins INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prediction_items (
    item_key TEXT PRIMARY KEY,
    item_label TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('instant', 'longterm')),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'locked', 'settled')),
    opened_at TEXT NOT NULL,
    locked_at TEXT
);

CREATE TABLE IF NOT EXISTS user_predictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nickname TEXT NOT NULL,
    item_key TEXT NOT NULL,
    prediction TEXT NOT NULL,
    last_changed_at TEXT NOT NULL,
    settled INTEGER NOT NULL DEFAULT 0,
    coins_earned INTEGER NOT NULL DEFAULT 0,
    UNIQUE (nickname, item_key),
    FOREIGN KEY (nickname) REFERENCES prophet_users(nickname),
    FOREIGN KEY (item_key) REFERENCES prediction_items(item_key)
);

CREATE TABLE IF NOT EXISTS settlement_events (
    item_key TEXT PRIMARY KEY,
    correct_answer TEXT NOT NULL,
    settled_at TEXT NOT NULL,
    FOREIGN KEY (item_key) REFERENCES prediction_items(item_key)
);
