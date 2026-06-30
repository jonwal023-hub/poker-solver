-- =============================================================================
-- POKER SOLVER PLATFORM: PRODUCTION DATABASE SCHEMA v2.0
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TYPE player_position AS ENUM ('BTN', 'SB', 'BB', 'UTG', 'MP', 'HJ', 'CO');
CREATE TYPE street_type AS ENUM ('PREFLOP', 'FLOP', 'TURN', 'RIVER');
CREATE TYPE action_type AS ENUM ('FOLD', 'CHECK', 'CALL', 'BET', 'RAISE', 'ALL_IN');

-- ============================================================================
-- TABLE 1: users
-- ============================================================================
CREATE TABLE users (
    user_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username        VARCHAR(50) UNIQUE NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- TABLE 2: sessions
-- ============================================================================
CREATE TABLE sessions (
    session_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    session_name    VARCHAR(255) NOT NULL,
    stakes          VARCHAR(20) NOT NULL,
    site            VARCHAR(50),
    total_hands     INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);

-- ============================================================================
-- TABLE 3: hands
-- ============================================================================
CREATE TABLE hands (
    hand_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    hero_cards      VARCHAR(6) NOT NULL,
    board_cards     VARCHAR(15),
    position        player_position NOT NULL,
    result_bb       DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    pot_size        DOUBLE PRECISION NOT NULL,
    showdown        BOOLEAN NOT NULL DEFAULT FALSE,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_hands_session_id_timestamp ON hands(session_id, timestamp DESC);

-- ============================================================================
-- TABLE 4: hand_actions
-- ============================================================================
CREATE TABLE hand_actions (
    action_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hand_id         UUID NOT NULL REFERENCES hands(hand_id) ON DELETE CASCADE,
    street          street_type NOT NULL,
    player          VARCHAR(50) NOT NULL,
    action          action_type NOT NULL,
    size_bb         DOUBLE PRECISION,
    action_order    INT NOT NULL,
    CONSTRAINT chk_action_size CHECK (
        (action IN ('BET', 'RAISE', 'ALL_IN') AND size_bb IS NOT NULL AND size_bb > 0) OR
        (action IN ('FOLD', 'CHECK', 'CALL') AND size_bb IS NULL)
    )
);
CREATE INDEX idx_hand_actions_hand_id_order ON hand_actions(hand_id, action_order ASC);

-- ============================================================================
-- TABLE 5: solver_analysis
-- ============================================================================
CREATE TABLE solver_analysis (
    analysis_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hand_id             UUID NOT NULL REFERENCES hands(hand_id) ON DELETE CASCADE,
    street              street_type NOT NULL,
    recommended_action  VARCHAR(50) NOT NULL,
    actual_action       VARCHAR(50) NOT NULL,
    ev_recommended      DOUBLE PRECISION NOT NULL,
    ev_actual           DOUBLE PRECISION NOT NULL,
    ev_loss             DOUBLE PRECISION NOT NULL,
    solver_version      VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    CONSTRAINT chk_positive_loss CHECK (ev_loss >= 0)
);
CREATE INDEX idx_solver_analysis_hand_id ON solver_analysis(hand_id, street);

-- ============================================================================
-- TABLE 6: decision_snapshots  (ReBeL — compressed Public Belief State)
-- ============================================================================
CREATE TABLE decision_snapshots (
    snapshot_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hand_id             UUID NOT NULL REFERENCES hands(hand_id) ON DELETE CASCADE,
    street              street_type NOT NULL,
    state_hash          VARCHAR(64) NOT NULL,
    pot_size            DOUBLE PRECISION NOT NULL,
    spr                 DOUBLE PRECISION NOT NULL,
    board_texture       VARCHAR(100),
    hero_features       JSONB NOT NULL DEFAULT '{}',
    villain_features    JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_decision_snapshots_state_hash ON decision_snapshots(state_hash);
CREATE INDEX idx_decision_snapshots_features ON decision_snapshots USING GIN (hero_features, villain_features);
CREATE INDEX idx_decision_snapshots_hand_id ON decision_snapshots(hand_id, street);

-- ============================================================================
-- TABLE 7: opponent_profiles
-- ============================================================================
CREATE TABLE opponent_profiles (
    opponent_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    screen_name         VARCHAR(50) NOT NULL,
    hands_seen          INT NOT NULL DEFAULT 0,
    vpip                DOUBLE PRECISION DEFAULT 0.0,
    pfr                 DOUBLE PRECISION DEFAULT 0.0,
    aggression          DOUBLE PRECISION DEFAULT 0.0,
    river_bluff_freq    DOUBLE PRECISION DEFAULT 0.0,
    fold_to_cbet        DOUBLE PRECISION DEFAULT 0.0,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, screen_name)
);
CREATE INDEX idx_opponent_profiles_user_id ON opponent_profiles(user_id);

-- ============================================================================
-- TABLE 8: analytics_cache
-- ============================================================================
CREATE TABLE analytics_cache (
    cache_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    metric_name     VARCHAR(100) NOT NULL,
    metric_value    JSONB NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, metric_name)
);
CREATE INDEX idx_analytics_cache_user_id ON analytics_cache(user_id);

-- ============================================================================
-- VIEW: hand_review  →  what GET /hands/{id} maps to. One query, zero app logic.
-- ============================================================================
CREATE VIEW hand_review AS
SELECT
    h.hand_id, h.hero_cards, h.board_cards, h.position,
    h.result_bb, h.pot_size, h.showdown, h.timestamp,
    (SELECT json_agg(json_build_object(
        'street', ha.street, 'player', ha.player, 'action', ha.action,
        'size_bb', ha.size_bb, 'order', ha.action_order
     ) ORDER BY ha.action_order ASC)
     FROM hand_actions ha WHERE ha.hand_id = h.hand_id) AS action_sequence,
    (SELECT json_agg(json_build_object(
        'street', sa.street, 'recommended', sa.recommended_action,
        'actual', sa.actual_action, 'ev_recommended', sa.ev_recommended,
        'ev_actual', sa.ev_actual, 'ev_loss', sa.ev_loss,
        'solver_version', sa.solver_version
     ) ORDER BY sa.street)
     FROM solver_analysis sa WHERE sa.hand_id = h.hand_id) AS analysis,
    (SELECT json_agg(json_build_object(
        'street', ds.street, 'state_hash', ds.state_hash, 'spr', ds.spr,
        'board_texture', ds.board_texture, 'hero_features', ds.hero_features,
        'villain_features', ds.villain_features
     ) ORDER BY ds.street)
     FROM decision_snapshots ds WHERE ds.hand_id = h.hand_id) AS snapshots
FROM hands h;
