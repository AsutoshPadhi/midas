"""Expense categorization logic"""
from typing import Optional, Dict
from app.llm.client import get_llm_client
from app.llm.prompts import CATEGORY_REFINEMENT_PROMPT
import logging

logger = logging.getLogger(__name__)

# Default categories
DEFAULT_CATEGORIES = [
    "Food & Dining",
    "Groceries",
    "Family",
    "Transportation",
    "Travel & Lodging",
    "Office Supplies",
    "Entertainment",
    "Utilities",
    "Healthcare",
    "Shopping",
    "Personal Care",
    "Other"
]


class ExpenseCategorizer:
    """Categorize expenses using LLM"""
    
    def __init__(self):
        self.llm_client = get_llm_client()
        self.categories = DEFAULT_CATEGORIES
    
    def categorize_expense(
        self,
        merchant: str,
    ) -> Dict[str, any]:
        """
        Categorize an expense using LLM
        
        Args:
            merchant: Merchant/counterparty name
            
        Returns:
            Dictionary with category only
        """
        prompt = CATEGORY_REFINEMENT_PROMPT.format(
            merchant=merchant,
        )
        
        try:
            result = self.llm_client.parse_json_response(
                prompt,
                temperature=0.0,
                max_tokens=200
            )
            
            if result and "category" in result:
                logger.info(f"Categorized '{merchant}' as '{result.get('category')}'")
                return {"category": result.get("category")}
            else:
                logger.warning(f"Failed to categorize expense for {merchant}")
                return {
                    "category": "Other",
                }
        
        except Exception as e:
            logger.error(f"Error categorizing expense: {e}")
            return {
                "category": "Other",
            }
    
    def get_categories(self) -> list:
        """Get list of available categories"""
        return self.categories
    
    def add_custom_category(self, category: str) -> None:
        """Add a custom category"""
        if category not in self.categories:
            self.categories.append(category)
            logger.info(f"Added custom category: {category}")


# Global categorizer instance
_categorizer: Optional[ExpenseCategorizer] = None


def get_expense_categorizer() -> ExpenseCategorizer:
    """Get or create global expense categorizer instance"""
    global _categorizer
    if _categorizer is None:
        _categorizer = ExpenseCategorizer()
    return _categorizer
