"""Extract and parse expenses from email using LLM"""
from typing import List, Dict, Optional
from app.llm.client import get_llm_client
from app.llm.prompts import (
    EXPENSE_EXTRACTION_PROMPT,
    BANK_EMAIL_CLASSIFICATION_PROMPT,
    BODY_FILTER_PROMPT,
)
from app.expenses.categorizer import get_expense_categorizer
import logging

logger = logging.getLogger(__name__)


class ExpenseExtractor:
    """Extract expenses from email content using LLM"""

    def __init__(self):
        self.llm_client = get_llm_client()
        self.expense_categorizer = get_expense_categorizer()

    def extract_expenses(
        self,
        email_content: str,
        email_subject: str = "",
        email_sender: str = ""
    ) -> Optional[Dict]:
        """
        Extract expenses from email content

        Args:
            email_content: The email body text
            email_subject: Email subject line
            email_sender: Email sender address

        Returns:
            Dictionary with extracted expenses and metadata
        """
        # Prepare the prompt with email content
        full_content = f"Subject: {email_subject}\nFrom: {email_sender}\n\n{email_content}"
        prompt = EXPENSE_EXTRACTION_PROMPT.format(email_content=full_content)

        try:
            result = self.llm_client.parse_json_response(
                prompt,
                temperature=0.1,
                max_tokens=1000
            )

            if result:
                logger.info(f"Extracted {len(result.get('expenses', []))} expenses from email")
                return result
            else:
                logger.warning("Failed to extract expenses from email")
                return None

        except Exception as e:
            logger.error(f"Error extracting expenses: {e}")
            return None

    def extract_batch(
        self,
        emails: List[Dict]
    ) -> List[Dict]:
        """
        Extract expenses from multiple emails

        Args:
            emails: List of email dictionaries with 'content', 'subject', 'sender'

        Returns:
            List of extraction results
        """
        results = []

        for email in emails:
            result = self.extract_expenses(
                email_content=email.get("content", ""),
                email_subject=email.get("subject", ""),
                email_sender=email.get("sender", "")
            )

            if result:
                result["email_id"] = email.get("id")
                results.append(result)

        logger.info(f"Extracted expenses from {len(results)}/{len(emails)} emails")
        return results

    def classify_bank_email(
        self,
        email_content: str,
        email_subject: str = "",
        email_sender: str = "",
        email_snippet: str = "",
    ) -> Optional[Dict]:
        """Classify if an email is bank-related using LLM."""
        logger.info(
            "Classifying email sender=%s subject_preview=%s body_chars=%d",
            (email_sender or "")[:120],
            (email_subject or "")[:120],
            len(email_content or ""),
        )
        prompt = BANK_EMAIL_CLASSIFICATION_PROMPT.format(
            email_subject=email_subject,
            email_sender=email_sender,
            email_snippet=email_snippet,
            email_content=email_content,
        )

        try:
            result = self.llm_client.parse_json_response(
                prompt,
                temperature=0.0,
                max_tokens=1000,
            )
            if result:
                logger.info(
                    "Bank classification result is_bank_email=%s confidence=%s",
                    result.get("is_bank_email"),
                    result.get("confidence"),
                )
                return result
        except Exception as e:
            logger.error(f"Error classifying bank email: {e}")

        logger.warning("Bank classification returned no result")

        return None

    def _body_is_transaction_email(self, email_content: str) -> bool:
        """Use LLM to check body/snippet before full extraction."""
        # Keep Gate 1 lightweight by limiting input size.
        candidate_content = (email_content or "")[:2000]
        prompt = BODY_FILTER_PROMPT.format(email_content=candidate_content)
        try:
            result = self.llm_client.parse_json_response(prompt, temperature=0.0, max_tokens=1000)
            is_transaction = bool(result and result.get("is_transaction_email") is True)
            return is_transaction
        except Exception as e:
            logger.error("Body filter LLM error content_preview=%s error=%s", candidate_content[:100], e)
            return False

    def _categorize_counterparty(self, counterparty: Optional[str]) -> str:
        """Return category for a transaction counterparty using the expense categorizer."""
        if not counterparty:
            return "Other"

        try:
            result = self.expense_categorizer.categorize_expense(merchant=counterparty)
            return result.get("category", "Other")
        except Exception as e:
            logger.error("Counterparty categorization failed counterparty=%s error=%s", counterparty, e)
            return "Other"

    def _attach_primary_transaction_fields(self, email: Dict, classification: Dict) -> None:
        """Project first extracted transaction into top-level fields for easier client use."""
        transactions = classification.get("transactions") or []
        primary = transactions[0] if transactions else {}

        email["transaction_amount"] = primary.get("amount")
        email["transaction_currency"] = primary.get("currency")
        email["transaction_type"] = primary.get("direction")
        email["transaction_counterparty"] = primary.get("counterparty")
        email["transaction_timestamp"] = primary.get("timestamp")
        email["transaction_category"] = primary.get("category")

    def enrich_email_with_bank_classification(self, email: Dict) -> Optional[Dict]:
        """Attach bank classification and extracted transaction fields to an email dict."""
        classification = self.classify_bank_email(
            email_content=email.get("body_text") or email.get("snippet", ""),
            email_subject=email.get("subject", ""),
            email_sender=email.get("sender", ""),
            email_snippet=email.get("snippet", ""),
        )

        if not classification:
            return None

        transactions = classification.get("transactions") or []
        for transaction in transactions:
            transaction["category"] = self._categorize_counterparty(transaction.get("counterparty"))

        email["bank_classification"] = classification
        self._attach_primary_transaction_fields(email, classification)
        return classification

    def _collect_transaction_candidates(self, emails: List[Dict]) -> List[Dict]:
        """Gate 1: collect emails that look like transaction notifications."""
        candidates: List[Dict] = []

        for email in emails:
            subject = email.get("subject", "")
            gate1_content = (email.get("body_text") or email.get("snippet", ""))

            if not self._body_is_transaction_email(gate1_content):
                logger.info("Skipping (body/snippet not transaction) subject=%s", subject[:120])
                continue

            candidates.append(email)

        logger.info("Filtered Messages = %d", len(candidates))
        return candidates

    def _extract_bank_details_from_candidates(self, candidate_emails: List[Dict]) -> List[Dict]:
        """Gate 2: run detailed extraction/classification on candidate emails only."""
        bank_emails: List[Dict] = []

        for email in candidate_emails:
            subject = email.get("subject", "")
            sender = email.get("sender", "")
            body_text = email.get("body_text") or ""
            snippet = email.get("snippet", "")

            logger.info(
                "Candidate matched, running LLM extraction sender=%s subject=%s",
                sender[:80],
                subject[:120],
            )

            classification = self.classify_bank_email(
                email_content=body_text or snippet,
                email_subject=subject,
                email_sender=sender,
                email_snippet=snippet,
            )

            if not classification:
                continue

            transactions = classification.get("transactions") or []
            for transaction in transactions:
                transaction["category"] = self._categorize_counterparty(transaction.get("counterparty"))

            email["bank_classification"] = classification
            self._attach_primary_transaction_fields(email, classification)
            if classification.get("is_bank_email") is True:
                bank_emails.append(email)

        return bank_emails

    def filter_bank_emails(self, emails: List[Dict]) -> List[Dict]:
        """Return only emails classified as bank transaction emails.

        Gate 1 (cheap): Body/snippet LLM check - skip if no transaction signal.
        Gate 2 (LLM):   Send the email body to the LLM for full extraction.
        """
        logger.info("Filtering bank emails from %d fetched emails", len(emails))

        candidate_emails = self._collect_transaction_candidates(emails)
        bank_emails = self._extract_bank_details_from_candidates(candidate_emails)

        logger.info(
            "Bank filtering complete. selected=%d candidates=%d total=%d",
            len(bank_emails),
            len(candidate_emails),
            len(emails),
        )
        return bank_emails


# Global expense extractor instance
_extractor: Optional[ExpenseExtractor] = None


def get_expense_extractor() -> ExpenseExtractor:
    """Get or create global expense extractor instance"""
    global _extractor
    if _extractor is None:
        _extractor = ExpenseExtractor()
    return _extractor
