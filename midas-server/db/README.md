# User Identity SQLite Schema

This directory contains a standalone SQLite schema and database for user identity metadata.

## Database File

- `midas.sqlite3`

## Schema File

- `schema.sql`

## Initialization Script

- `init_sqlite.py`

Run:

```bash
uv run python db/init_sqlite.py
```

## Table Names and Keys

### `users`
- `user_uuid` (`TEXT`, PK): Unique user identifier (UUID string).
- `display_name` (`TEXT`, default: `User`): User display name.
- `google_id` (`TEXT`, unique): Google subject identifier.
- `google_access_token` (`TEXT`, nullable): Current Google access token.
- `google_refresh_token` (`TEXT`, nullable): Refresh token for renewals.
- `google_token_expiry` (`TEXT`, nullable): OAuth token expiry timestamp.
- `google_token_scope` (`TEXT`, nullable): Granted OAuth scopes.
- `last_synced_at` (`TEXT`, nullable): Last sync timestamp.
- `created_at`, `updated_at` (`TEXT`): Audit timestamps.

### `user_emails`
- `user_email_id` (`INTEGER`, PK, autoincrement): Surrogate key for email records.
- `user_uuid` (`TEXT`, FK -> `users.user_uuid`): Owning user UUID.
- `email_address` (`TEXT`): Email address associated with the user.
- `is_primary` (`INTEGER`, 0/1, default: `1`): Marks primary login email.
- `created_at` (`TEXT`, default current timestamp): Row creation time.
- Constraints: `UNIQUE(user_uuid, email_address)`.

### `user_family_links`
- `user_uuid` (`TEXT`, FK -> `users.user_uuid`): Base user UUID.
- `family_member_uuid` (`TEXT`, FK -> `users.user_uuid`): Related family member UUID.
- `relation_label` (`TEXT`, nullable): Optional relation (for example, `spouse`, `child`).
- `created_at` (`TEXT`, default current timestamp): Row creation time.
- Composite PK: `(user_uuid, family_member_uuid)`.
- Constraint: cannot self-link.

### `expenses`
- `id` (`INTEGER`, PK, autoincrement): Expense record identifier.
- `user_uuid` (`TEXT`, FK -> `users.user_uuid`): Owning user.
- `amount` (`NUMERIC`): Transaction amount.
- `currency` (`TEXT`, default: `USD`): Currency code.
- `merchant` (`TEXT`): Merchant or counterparty.
- `description` (`TEXT`, nullable): Expense description.
- `category` (`TEXT`): Expense category.
- `transaction_date` (`TEXT`): Transaction timestamp.
- `email_message_id` (`TEXT`, nullable): Source email message id.
- `notes` (`TEXT`, nullable): Optional note.
- `created_at`, `updated_at` (`TEXT`): Audit timestamps.

### `email_messages`
- `id` (`INTEGER`, PK, autoincrement): Email record identifier.
- `user_uuid` (`TEXT`, FK -> `users.user_uuid`): Owning user.
- `gmail_message_id` (`TEXT`, unique): Gmail message identifier.
- `subject`, `sender`, `body_text`, `body_html`: Message fields.
- `received_at` (`TEXT`): Original received timestamp.
- `processed` (`INTEGER`, 0/1): Processing status.
- `created_at` (`TEXT`): Row creation time.

### `transactions`
- `txn_id` (`INTEGER`, PK, autoincrement): Transaction identifier.
- `user_uuid` (`TEXT`, FK -> `users.user_uuid`): Owning user id.
- `amount` (`NUMERIC`): Transaction amount.
- `direction` (`TEXT`): One of `debit`, `credit`, `unknown`.
- `counterparty` (`TEXT`): Transaction counterparty.
- `category` (`TEXT`): Assigned transaction category.
- `card_last_4_digits` (`TEXT`, nullable): Card last 4 digits.
- `account_last_4_digits` (`TEXT`, nullable): Account last 4 digits.
- `txn_timestamp` (`TEXT`): Transaction timestamp (ISO-8601 recommended).
- `txn_fingerprint` (`TEXT`, unique): Deterministic hash for idempotent de-duplication.

## Why this design

- `List<emails>` is modeled as a child table (`user_emails`) for one-to-many support.
- `Family -> list<UUID>` is modeled as an adjacency table (`user_family_links`) for many-to-many relations.
- OAuth tokens remain in `users` to preserve login/refresh flow.
- Expense and email-message tables preserve earlier app behavior on top of UUID users.
