"""LLM prompt templates for expense extraction"""

EXPENSE_EXTRACTION_PROMPT = """
Analyze the following email content and extract expense information.

Email Content:
{email_content}

Please extract:
1. Amount (numeric value)
2. Currency (e.g., USD, EUR)
3. Merchant/Vendor name
4. Description of the expense
5. Expense type/category (e.g., food, travel, office supplies, etc.)
6. Date of transaction (if available)

Format your response as JSON with the following structure:
{{
    "expenses": [
        {{
            "amount": number,
            "currency": "string",
            "merchant": "string",
            "description": "string",
            "category": "string",
            "date": "YYYY-MM-DD"
        }}
    ],
    "confidence": "high/medium/low",
    "notes": "any additional notes"
}}

If no expenses are found, return:
{{"expenses": [], "confidence": "high", "notes": "No expenses found in this email"}}
"""

CATEGORY_REFINEMENT_PROMPT = """
Given a merchant/counterparty name, determine the most appropriate expense category.
If the counterparty sounds like person's name, categorize it as Individual

Merchant/Counterparty:
- {merchant}

Available categories:
- Food & Dining
- Groceries
- Family
- Individual
- Investments
- Transportation
- Travel & Lodging
- Office Supplies
- Entertainment
- Utilities
- Healthcare
- Shopping
- Personal Care
- Other

Return ONLY the category.

Format your response as JSON:
{{
    "category": "string"
}}
"""

EXPENSE_SUMMARY_PROMPT = """
Summarize the following expenses by category for the user's review.

Expenses:
{expenses_list}

Please provide:
1. Total amount by category
2. Number of transactions by category
3. Most common merchants
4. Insights about spending patterns

Format as a clear, readable summary.
"""

BODY_FILTER_PROMPT = """
Does the following email body/snippet indicate a bank/financial transaction notification?
Only answer based on this content.

Email Content:
{email_content}

Examples that ARE transaction notifications:
- "Your a/c XXXX1234 is debited by INR 520.00 via UPI"
- "UPI txn of Rs 199 completed"
- "A payment was made using your Credit Card"
- "Account update for your HDFC Bank A/c"

Return strictly valid JSON:
{{"is_transaction_email": true_or_false}}
"""

BANK_EMAIL_CLASSIFICATION_PROMPT = """
The following email may be a bank/financial transaction notification.
Extract ALL transaction details from the email body.

Email metadata and content:
Subject: {email_subject}
Sender: {email_sender}
Snippet: {email_snippet}

Body:
{email_content}

Return a valid JSON in this format:
{{
    "is_bank_email": true_or_false,
    "confidence": "high|medium|low",
    "bank_name": "string or null",
    "reason": "brief reason",
    "transactions": [
        {{
            "amount": number_or_null,
            "currency": "string or null",
            "direction": "debit|credit|unknown",
            "counterparty": "string or null",
            "card_last_4_digits": "string or null",
            "account_last_4_digits": "string or null",
            "payment_method": "card|bank_transfer|upi|unknown",
            "timestamp": "ISO-8601 datetime string or null"
        }}
    ]
}}

EXTRACTION RULES:

1. AMOUNT: Look for "INR X,XXX.XX", "Rs. XXX.XX", "Rs X.X", "amount of INR", "Amount: INR"
   - Extract numeric value only, strip commas. Currency is typically INR.

2. DIRECTION:
   - "DEBITED" / "debited" / "charge" / "payment made" / "spent" -> "debit"
   - "CREDITED" / "credited" / "received" -> "credit"
   - Default to "unknown" if ambiguous

3. COUNTERPARTY:
   - Debit: "to [entity]", "at [merchant]", "towards [payee]"
   - Credit: "from [entity]", "from [person]"
   - Preserve exact name (e.g., "RAZ*Swiggy")

4. CARD LAST 4 DIGITS: Patterns like "ending in 0227", "ending 5769", "XX5769", "Card ending 5769"

5. ACCOUNT LAST 4 DIGITS: Patterns like "XXXX4044", "account xxxxxxxxxx2248"

6. PAYMENT METHOD: "UPI" -> "upi"; "NEFT"/"IMPS"/"RTGS" -> "bank_transfer"; "Credit Card"/"Card" -> "card"

7. TIMESTAMP: Convert any date/time to ISO-8601 UTC. Assume IST if no timezone given. Use 00:00:00 if time is missing.

Set is_bank_email=false only if the body contains NO transaction details at all.
If a field cannot be reliably extracted, set it to null.
Extract ALL transactions present in the email (there may be multiple).
"""
