-- SQLite schema for Midas.
-- Uses UUID-based users and normalized email/family relations.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_uuid TEXT PRIMARY KEY,
    display_name TEXT NOT NULL DEFAULT 'User',
    google_id TEXT UNIQUE,
    google_access_token TEXT,
    google_refresh_token TEXT,
    google_token_expiry TEXT,
    google_token_scope TEXT,
    last_synced_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_emails (
    user_email_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_uuid TEXT NOT NULL,
    email_address TEXT NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 1 CHECK (is_primary IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_uuid, email_address),
    FOREIGN KEY (user_uuid) REFERENCES users(user_uuid) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_family_links (
    user_uuid TEXT NOT NULL,
    family_member_uuid TEXT NOT NULL,
    relation_label TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_uuid, family_member_uuid),
    FOREIGN KEY (user_uuid) REFERENCES users(user_uuid) ON DELETE CASCADE,
    FOREIGN KEY (family_member_uuid) REFERENCES users(user_uuid) ON DELETE CASCADE,
    CHECK (user_uuid <> family_member_uuid)
);

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_uuid TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    merchant TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,
    transaction_date TEXT NOT NULL,
    email_message_id TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_uuid) REFERENCES users(user_uuid) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS email_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_uuid TEXT NOT NULL,
    gmail_message_id TEXT UNIQUE,
    subject TEXT,
    sender TEXT,
    body_text TEXT,
    body_html TEXT,
    received_at TEXT NOT NULL,
    processed INTEGER NOT NULL DEFAULT 0 CHECK (processed IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_uuid) REFERENCES users(user_uuid) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transactions (
    txn_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_uuid TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('debit', 'credit', 'unknown')),
    counterparty TEXT NOT NULL,
    category TEXT NOT NULL,
    card_last_4_digits TEXT,
    account_last_4_digits TEXT,
    txn_timestamp TEXT NOT NULL,
    txn_fingerprint TEXT NOT NULL,
    FOREIGN KEY (user_uuid) REFERENCES users(user_uuid) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_emails_user_uuid ON user_emails(user_uuid);
CREATE INDEX IF NOT EXISTS idx_user_emails_email_address ON user_emails(email_address);
CREATE INDEX IF NOT EXISTS idx_family_links_user_uuid ON user_family_links(user_uuid);
CREATE INDEX IF NOT EXISTS idx_family_links_member_uuid ON user_family_links(family_member_uuid);
CREATE INDEX IF NOT EXISTS idx_expenses_user_uuid_date ON expenses(user_uuid, transaction_date);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);
CREATE INDEX IF NOT EXISTS idx_email_messages_user_uuid ON email_messages(user_uuid);
CREATE INDEX IF NOT EXISTS idx_email_messages_processed ON email_messages(processed);
CREATE INDEX IF NOT EXISTS idx_transactions_user_uuid_ts ON transactions(user_uuid, txn_timestamp);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category);
CREATE UNIQUE INDEX IF NOT EXISTS ux_transactions_fingerprint ON transactions(txn_fingerprint);
