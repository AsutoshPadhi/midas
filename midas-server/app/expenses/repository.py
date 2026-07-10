"""SQLite repositories for expense and email message operations."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import logging

from app.database.base import get_connection
from app.expenses.schemas import ExpenseCreate, ExpenseUpdate

logger = logging.getLogger(__name__)


def _row_to_expense_dict(row: Any) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "user_id": row["user_uuid"],
        "amount": Decimal(str(row["amount"])),
        "currency": row["currency"],
        "merchant": row["merchant"],
        "description": row["description"],
        "category": row["category"],
        "transaction_date": datetime.fromisoformat(row["transaction_date"]),
        "notes": row["notes"],
        "created_at": datetime.fromisoformat(row["created_at"]),
        "updated_at": datetime.fromisoformat(row["updated_at"]),
    }


class ExpenseRepository:
    """Repository for expense database operations."""
    
    @staticmethod
    def create_expense(user_uuid: str, expense: ExpenseCreate) -> Dict[str, Any]:
        """Create a new expense."""
        now_iso = datetime.utcnow().isoformat()
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO expenses (
                    user_uuid, amount, currency, merchant, description, category,
                    transaction_date, email_message_id, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_uuid,
                    str(expense.amount),
                    expense.currency,
                    expense.merchant,
                    expense.description,
                    expense.category,
                    expense.transaction_date.isoformat(),
                    expense.email_message_id,
                    expense.notes,
                    now_iso,
                    now_iso,
                ),
            )
            expense_id = cursor.lastrowid
            row = connection.execute(
                "SELECT * FROM expenses WHERE id = ? AND user_uuid = ?",
                (expense_id, user_uuid),
            ).fetchone()
        logger.info("Created expense %s for user %s", expense_id, user_uuid)
        return _row_to_expense_dict(row)
    
    @staticmethod
    def get_expense(expense_id: int, user_uuid: str) -> Optional[Dict[str, Any]]:
        """Get expense by ID."""
        with get_connection() as connection:
            row = connection.execute(
                "SELECT * FROM expenses WHERE id = ? AND user_uuid = ?",
                (expense_id, user_uuid),
            ).fetchone()
        if not row:
            return None
        return _row_to_expense_dict(row)
    
    @staticmethod
    def get_user_expenses(
        user_uuid: str,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get expenses for a user with optional filters."""
        query = "SELECT * FROM expenses WHERE user_uuid = ?"
        params: List[Any] = [user_uuid]

        if category:
            query += " AND category = ?"
            params.append(category)
        if start_date:
            query += " AND transaction_date >= ?"
            params.append(start_date.isoformat())
        if end_date:
            query += " AND transaction_date <= ?"
            params.append(end_date.isoformat())

        query += " ORDER BY transaction_date DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])

        with get_connection() as connection:
            rows = connection.execute(query, params).fetchall()

        return [_row_to_expense_dict(row) for row in rows]
    
    @staticmethod
    def update_expense(
        expense_id: int,
        user_uuid: str,
        expense_update: ExpenseUpdate
    ) -> Optional[Dict[str, Any]]:
        """Update an expense."""
        existing = ExpenseRepository.get_expense(expense_id, user_uuid)
        if not existing:
            return None

        update_data = expense_update.model_dump(exclude_unset=True)
        fields: List[str] = []
        values: List[Any] = []
        for key, value in update_data.items():
            if key == "transaction_date" and value is not None:
                value = value.isoformat()
            fields.append(f"{key} = ?")
            values.append(value)

        if fields:
            fields.append("updated_at = ?")
            values.append(datetime.utcnow().isoformat())
            values.extend([expense_id, user_uuid])
            with get_connection() as connection:
                connection.execute(
                    f"UPDATE expenses SET {', '.join(fields)} WHERE id = ? AND user_uuid = ?",
                    values,
                )

        logger.info("Updated expense %s", expense_id)
        return ExpenseRepository.get_expense(expense_id, user_uuid)
    
    @staticmethod
    def delete_expense(expense_id: int, user_uuid: str) -> bool:
        """Delete an expense."""
        with get_connection() as connection:
            cursor = connection.execute(
                "DELETE FROM expenses WHERE id = ? AND user_uuid = ?",
                (expense_id, user_uuid),
            )
        if cursor.rowcount <= 0:
            return False
        logger.info("Deleted expense %s", expense_id)
        return True
    
    @staticmethod
    def get_expense_summary(
        user_uuid: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """Get expense summary by category."""
        query = """
            SELECT category, SUM(amount) AS total, COUNT(id) AS count, AVG(amount) AS average
            FROM expenses
            WHERE user_uuid = ?
        """
        params: List[Any] = [user_uuid]

        if start_date:
            query += " AND transaction_date >= ?"
            params.append(start_date.isoformat())
        if end_date:
            query += " AND transaction_date <= ?"
            params.append(end_date.isoformat())

        query += " GROUP BY category"

        with get_connection() as connection:
            rows = connection.execute(query, params).fetchall()

        return {
            "by_category": [
                {
                    "category": row["category"],
                    "total": Decimal(str(row["total"] or 0)),
                    "count": row["count"],
                    "average": Decimal(str(row["average"] or 0)),
                }
                for row in rows
            ]
        }


class EmailMessageRepository:
    """Repository for email message operations."""
    
    @staticmethod
    def create_email_message(
        user_uuid: str,
        gmail_id: str,
        subject: str,
        sender: str,
        body_text: str,
        body_html: Optional[str] = None,
        received_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Create a new email message record."""
        if isinstance(received_at, str):
            received_iso = received_at
        else:
            received_iso = (received_at or datetime.utcnow()).isoformat()
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO email_messages (
                    user_uuid, gmail_message_id, subject, sender, body_text,
                    body_html, received_at, processed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (user_uuid, gmail_id, subject, sender, body_text, body_html, received_iso),
            )
            row = connection.execute(
                "SELECT * FROM email_messages WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return dict(row)
    
    @staticmethod
    def get_unprocessed_emails(user_uuid: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get unprocessed emails for a user."""
        with get_connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM email_messages
                WHERE user_uuid = ? AND processed = 0
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_uuid, limit),
            ).fetchall()
        return [dict(row) for row in rows]
    
    @staticmethod
    def mark_as_processed(email_id: int) -> None:
        """Mark email as processed."""
        with get_connection() as connection:
            connection.execute(
                "UPDATE email_messages SET processed = 1 WHERE id = ?",
                (email_id,),
            )
