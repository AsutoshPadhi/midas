"""Email API routes"""
from datetime import datetime, timezone
import hashlib
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Header
from jose import JWTError

from app.auth.oauth import oauth_handler
from app.core.security import verify_token
from app.database.base import get_connection
from app.email.email_parser import EmailParser
from app.email.gmail_client import GmailClient
from app.expenses.expense_extractor import get_expense_extractor

router = APIRouter(prefix="/email", tags=["email"])


def _as_utc(dt: datetime) -> datetime:
    """Normalize datetimes from DB to UTC-aware for safe comparisons."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _get_user_record(user_uuid: str):
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT user_uuid, google_access_token, google_refresh_token, google_token_expiry, google_token_scope, last_synced_at
            FROM users WHERE user_uuid = ?
            """,
            (user_uuid,),
        ).fetchone()


def _update_user_tokens(
    user_uuid: str,
    access_token: str,
    refresh_token: Optional[str],
    token_expiry: Optional[str],
    token_scope: Optional[str],
) -> None:
    with get_connection() as connection:
        if refresh_token:
            connection.execute(
                """
                UPDATE users
                SET google_access_token = ?,
                    google_refresh_token = ?,
                    google_token_expiry = ?,
                    google_token_scope = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_uuid = ?
                """,
                (access_token, refresh_token, token_expiry, token_scope, user_uuid),
            )
        else:
            connection.execute(
                """
                UPDATE users
                SET google_access_token = ?,
                    google_token_expiry = ?,
                    google_token_scope = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_uuid = ?
                """,
                (access_token, token_expiry, token_scope, user_uuid),
            )


def _get_sync_after_timestamp(last_synced_at_raw: Optional[str]) -> datetime:
    """Return lower-bound timestamp for sync window.

    First sync: start of current month (UTC).
    Subsequent syncs: users.last_synced_at.
    """
    if last_synced_at_raw:
        try:
            return datetime.fromisoformat(last_synced_at_raw)
        except ValueError:
            pass

    now_utc = datetime.now(timezone.utc)
    return now_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _build_incremental_gmail_query(base_query: str, after_ts: datetime) -> str:
    """Append Gmail 'after:' constraint for incremental fetches."""
    if " after:" in f" {base_query}":
        return base_query
    after_clause = f"after:{after_ts.strftime('%Y/%m/%d')}"
    return f"{base_query} {after_clause}".strip()


def _mark_sync_completed(user_uuid: str, synced_at: datetime) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET last_synced_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_uuid = ?
            """,
            (synced_at.astimezone(timezone.utc).isoformat(), user_uuid),
        )


def _persist_transactions_from_bank_messages(user_uuid: str, bank_messages: list[dict]) -> int:
    """Persist extracted bank transactions from message payload into transactions table."""
    inserted = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        for message in bank_messages:
            classification = message.get("bank_classification") or {}
            transactions = classification.get("transactions") or []
            source_message_id = message.get("gmail_message_id") or ""

            for txn in transactions:
                amount = txn.get("amount")
                if amount is None:
                    # Skip records with no amount because amount is mandatory in schema.
                    continue

                direction = txn.get("direction") or "unknown"
                counterparty = txn.get("counterparty") or "Unknown"
                category = txn.get("category") or "Other"
                txn_timestamp = txn.get("timestamp") or now_iso
                card_last_4_digits = txn.get("card_last_4_digits")
                account_last_4_digits = txn.get("account_last_4_digits")

                fingerprint_payload = "|".join(
                    [
                        str(user_uuid),
                        str(amount),
                        str(direction),
                        str(counterparty),
                        str(category),
                        str(card_last_4_digits or ""),
                        str(account_last_4_digits or ""),
                        str(txn_timestamp),
                        str(source_message_id),
                    ]
                )
                txn_fingerprint = hashlib.sha256(fingerprint_payload.encode("utf-8")).hexdigest()

                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO transactions (
                        user_uuid,
                        amount,
                        direction,
                        counterparty,
                        category,
                        card_last_4_digits,
                        account_last_4_digits,
                        txn_timestamp,
                        txn_fingerprint
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_uuid,
                        amount,
                        direction,
                        counterparty,
                        category,
                        card_last_4_digits,
                        account_last_4_digits,
                        txn_timestamp,
                        txn_fingerprint,
                    ),
                )
                if cursor.rowcount > 0:
                    inserted += 1

    return inserted


def _list_transactions_for_user(user_uuid: str) -> list[dict]:
    """Return persisted transactions for a user ordered by latest timestamp first."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT txn_id, user_uuid, amount, direction, counterparty, category,
                   card_last_4_digits, account_last_4_digits, txn_timestamp
            FROM transactions
            WHERE user_uuid = ?
            ORDER BY txn_timestamp DESC, txn_id DESC
            """,
            (user_uuid,),
        ).fetchall()

    return [
        {
            "txn_id": row["txn_id"],
            "user_uuid": row["user_uuid"],
            "amount": row["amount"],
            "direction": row["direction"],
            "counterparty": row["counterparty"],
            "category": row["category"],
            "card_last_4_digits": row["card_last_4_digits"],
            "account_last_4_digits": row["account_last_4_digits"],
            "txn_timestamp": row["txn_timestamp"],
        }
        for row in rows
    ]


async def _run_bank_message_sync_driver(user_uuid: str, query: str, max_results: int) -> list[dict]:
    """Driver for bank message fetch, classification, persistence, and sync marker update."""
    user = _get_user_record(user_uuid)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not user["google_access_token"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Google access token found for this user. Please login again.",
        )

    now_utc = datetime.now(timezone.utc)
    token_expiry_raw = user["google_token_expiry"]
    token_expiry = datetime.fromisoformat(token_expiry_raw) if token_expiry_raw else None
    if token_expiry and _as_utc(token_expiry) <= now_utc:
        if not user["google_refresh_token"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google access token expired and no refresh token is available. Please login again.",
            )

        refreshed = await oauth_handler.refresh_access_token(user["google_refresh_token"])
        if not refreshed or not refreshed.get("access_token"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to refresh Google access token. Please login again.",
            )

        refreshed_expiry = None
        if refreshed.get("expires_at"):
            refreshed_expiry = datetime.fromtimestamp(
                int(refreshed.get("expires_at")), tz=timezone.utc
            ).isoformat()

        _update_user_tokens(
            user_uuid=user_uuid,
            access_token=refreshed.get("access_token"),
            refresh_token=refreshed.get("refresh_token"),
            token_expiry=refreshed_expiry,
            token_scope=refreshed.get("scope"),
        )
        user = _get_user_record(user_uuid)

    sync_started_at = datetime.now(timezone.utc)
    after_ts = _get_sync_after_timestamp(user["last_synced_at"])
    incremental_query = _build_incremental_gmail_query(query, after_ts)

    gmail_client = GmailClient(access_token=user["google_access_token"])
    parser = EmailParser()
    messages = gmail_client.get_messages(query=incremental_query, max_results=max_results)
    results = []

    for message in messages:
        message_id = message.get("id")
        if not message_id:
            continue

        details = gmail_client.get_message_details(message_id)
        if not details:
            continue

        headers = parser.extract_headers(details)
        text_body, html_body = parser.extract_body(details)

        results.append(
            {
                "gmail_message_id": message_id,
                "thread_id": details.get("threadId"),
                "subject": headers.get("subject", ""),
                "sender": headers.get("from", ""),
                "received_at": headers.get("date"),
                "snippet": details.get("snippet", ""),
                "body_text": text_body,
                "body_html": html_body,
            }
        )

    try:
        extractor = get_expense_extractor()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM not configured: {exc}",
        )

    results = extractor.filter_bank_emails(results)
    _persist_transactions_from_bank_messages(user_uuid, results)
    _mark_sync_completed(user_uuid, sync_started_at)
    return results


def get_current_user_for_email(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None, description="App JWT token (for browser testing)"),
) -> str:
    """Authenticate user using Bearer header or token query parameter."""
    jwt_token: Optional[str] = token
    if authorization and authorization.startswith("Bearer "):
        jwt_token = authorization[7:]

    if not jwt_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token. Use Bearer token or ?token=...",
        )

    try:
        payload = verify_token(jwt_token)
        user_uuid = str(payload.get("sub"))
        if not user_uuid:
            raise ValueError("Missing user UUID in token")
        return user_uuid
    except (JWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


@router.get("/messages")
async def fetch_messages(
    user_uuid: str = Depends(get_current_user_for_email),
    query: str = Query("in:inbox", description="Gmail query string"),
    max_results: int = Query(10, ge=1, le=100),
    classify_bank_with_llm: bool = Query(True, description="Classify emails using LLM"),
    bank_only: bool = Query(False, description="Return only emails classified as bank emails"),
):
    """Fetch Gmail messages for the authenticated user."""
    if bank_only and not classify_bank_with_llm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="bank_only=true requires classify_bank_with_llm=true",
        )

    user = _get_user_record(user_uuid)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not user["google_access_token"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Google access token found for this user. Please login again.",
        )

    # Refresh token if current access token is expired.
    now_utc = datetime.now(timezone.utc)
    token_expiry_raw = user["google_token_expiry"]
    token_expiry = datetime.fromisoformat(token_expiry_raw) if token_expiry_raw else None
    if token_expiry and _as_utc(token_expiry) <= now_utc:
        if not user["google_refresh_token"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google access token expired and no refresh token is available. Please login again.",
            )

        refreshed = await oauth_handler.refresh_access_token(user["google_refresh_token"])
        if not refreshed or not refreshed.get("access_token"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to refresh Google access token. Please login again.",
            )

        refreshed_expiry = None
        if refreshed.get("expires_at"):
            refreshed_expiry = datetime.fromtimestamp(
                int(refreshed.get("expires_at")), tz=timezone.utc
            ).isoformat()

        _update_user_tokens(
            user_uuid=user_uuid,
            access_token=refreshed.get("access_token"),
            refresh_token=refreshed.get("refresh_token"),
            token_expiry=refreshed_expiry,
            token_scope=refreshed.get("scope"),
        )
        user = _get_user_record(user_uuid)

    sync_started_at = datetime.now(timezone.utc)
    after_ts = _get_sync_after_timestamp(user["last_synced_at"])
    incremental_query = _build_incremental_gmail_query(query, after_ts)

    gmail_client = GmailClient(access_token=user["google_access_token"])
    parser = EmailParser()

    messages = gmail_client.get_messages(query=incremental_query, max_results=max_results)
    results = []

    for message in messages:
        message_id = message.get("id")
        if not message_id:
            continue

        details = gmail_client.get_message_details(message_id)
        if not details:
            continue

        headers = parser.extract_headers(details)
        text_body, html_body = parser.extract_body(details)

        results.append(
            {
                "gmail_message_id": message_id,
                "thread_id": details.get("threadId"),
                "subject": headers.get("subject", ""),
                "sender": headers.get("from", ""),
                "received_at": headers.get("date"),
                "snippet": details.get("snippet", ""),
                "body_text": text_body,
                "body_html": html_body,
            }
        )

    if classify_bank_with_llm:
        try:
            extractor = get_expense_extractor()
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"LLM not configured: {exc}",
            )

        if bank_only:
            results = extractor.filter_bank_emails(results)
        else:
            for email in results:
                extractor.enrich_email_with_bank_classification(email)

    _mark_sync_completed(user_uuid, sync_started_at)

    return {
        "count": len(results),
        "messages": results,
    }


@router.get("/messages/bank")
async def fetch_bank_messages(
    user_uuid: str = Depends(get_current_user_for_email),
    query: str = Query("in:inbox", description="Gmail query string"),
    max_results: int = Query(50, ge=1, le=100),
):
    """Fetch and classify only bank transaction emails using LLM."""
    results = await _run_bank_message_sync_driver(user_uuid, query, max_results)

    return {
        "count": len(results),
        "messages": results,
    }


@router.get("/transactions/sync")
async def sync_transactions_for_frontend(
    user_uuid: str = Depends(get_current_user_for_email),
    query: str = Query("in:inbox", description="Gmail query string"),
    max_results: int = Query(50, ge=1, le=100),
):
    """Run the bank-message sync driver and return persisted transaction rows for the user."""
    await _run_bank_message_sync_driver(user_uuid, query, max_results)
    transactions = _list_transactions_for_user(user_uuid)
    return {
        "count": len(transactions),
        "transactions": transactions,
    }
