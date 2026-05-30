CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_accounts (
    id BIGSERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    nickname TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_player_pool (
    id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    player_name TEXT NOT NULL,
    purchased_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (username, player_id)
);

CREATE TABLE IF NOT EXISTS hall_poll_definitions (
    id BIGSERIAL PRIMARY KEY,
    poll_key TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    subtitle TEXT NOT NULL,
    poll_type TEXT NOT NULL CHECK (poll_type IN ('player', 'team', 'custom')),
    options_json TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    display_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS polls (
    id BIGSERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    correct_answer TEXT,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS poll_options (
    id BIGSERIAL PRIMARY KEY,
    poll_id BIGINT NOT NULL REFERENCES polls(id),
    option_text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS votes (
    id BIGSERIAL PRIMARY KEY,
    poll_id BIGINT NOT NULL REFERENCES polls(id),
    voter_id TEXT NOT NULL,
    option_id BIGINT NOT NULL REFERENCES poll_options(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (poll_id, voter_id)
);

CREATE TABLE IF NOT EXISTS fantasy_teams (
    id BIGSERIAL PRIMARY KEY,
    owner_name TEXT NOT NULL,
    team_name TEXT NOT NULL,
    total_score REAL NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fantasy_team_players (
    id BIGSERIAL PRIMARY KEY,
    fantasy_team_id BIGINT NOT NULL REFERENCES fantasy_teams(id),
    player_id INTEGER NOT NULL,
    player_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS matchup_votes (
    id BIGSERIAL PRIMARY KEY,
    matchup_id TEXT NOT NULL,
    voter_id TEXT NOT NULL,
    selected_side TEXT NOT NULL CHECK (selected_side IN ('A', 'B')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
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
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hall_votes (
    id BIGSERIAL PRIMARY KEY,
    poll_key TEXT NOT NULL,
    voter_id TEXT NOT NULL,
    choice TEXT NOT NULL,
    voted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (poll_key, voter_id)
);

CREATE TABLE IF NOT EXISTS player_ratings (
    id BIGSERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL,
    voter_id TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (player_id, voter_id)
);

CREATE TABLE IF NOT EXISTS game_comments (
    id BIGSERIAL PRIMARY KEY,
    game_id TEXT NOT NULL,
    voter_id TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS comment_likes (
    id BIGSERIAL PRIMARY KEY,
    comment_id BIGINT NOT NULL REFERENCES game_comments(id) ON DELETE CASCADE,
    voter_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (comment_id, voter_id)
);

CREATE TABLE IF NOT EXISTS daily_checkins (
    id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    checkin_date TEXT NOT NULL,
    coins_earned INTEGER NOT NULL DEFAULT 150,
    UNIQUE (username, checkin_date)
);

CREATE TABLE IF NOT EXISTS prophet_users (
    id BIGSERIAL PRIMARY KEY,
    nickname TEXT UNIQUE NOT NULL,
    coins INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
    id BIGSERIAL PRIMARY KEY,
    nickname TEXT NOT NULL REFERENCES prophet_users(nickname),
    item_key TEXT NOT NULL REFERENCES prediction_items(item_key),
    prediction TEXT NOT NULL,
    last_changed_at TEXT NOT NULL,
    settled INTEGER NOT NULL DEFAULT 0,
    coins_earned INTEGER NOT NULL DEFAULT 0,
    UNIQUE (nickname, item_key)
);

CREATE TABLE IF NOT EXISTS settlement_events (
    item_key TEXT PRIMARY KEY REFERENCES prediction_items(item_key),
    correct_answer TEXT NOT NULL,
    settled_at TEXT NOT NULL
);
