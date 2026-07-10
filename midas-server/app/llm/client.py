"""LLM API client wrapper"""
from typing import Optional, Dict, Any
from app.config import settings
import logging
import re
import time
import uuid

logger = logging.getLogger(__name__)


class LLMClient:
    """Generic LLM client wrapper"""
    
    def __init__(self, provider: str = None, api_key: str = None, model: str = None):
        """
        Initialize LLM client
        
        Args:
            provider: LLM provider (openai, anthropic, etc.)
            api_key: API key for the provider
            model: Model name/ID
        """
        self.provider = provider or settings.llm_provider
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model

        # Ollama's OpenAI-compatible endpoint commonly accepts a dummy key.
        if self.provider == "ollama" and not self.api_key:
            self.api_key = "ollama"

        if not self.api_key:
            raise ValueError("LLM API key not configured")
        
        self._init_client()
    
    def _init_client(self):
        """Initialize the appropriate LLM client based on provider"""
        if self.provider in ("openai", "groq", "ollama"):
            try:
                from openai import OpenAI
                base_url = None
                if self.provider == "groq":
                    base_url = "https://api.groq.com/openai/v1"
                elif self.provider == "ollama":
                    base_url = settings.llm_base_url or "http://localhost:11434/v1"
                self.client = OpenAI(api_key=self.api_key, base_url=base_url)
                logger.info("LLM client initialized provider=%s model=%s", self.provider, self.model)
            except ImportError:
                logger.error("OpenAI package not installed")
                raise
        else:
            logger.warning(f"Provider {self.provider} not fully implemented")
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        retries: int = 3,
        retry_delay_seconds: float = 1.0,
        **kwargs
    ) -> Optional[str]:
        """
        Generate text using LLM
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            **kwargs: Additional parameters for the API
            
        Returns:
            Generated text or None if error
        """
        request_id = str(uuid.uuid4())[:8]
        prompt_chars = len(prompt or "")
        logger.info(
            "LLM request start id=%s provider=%s model=%s prompt_chars=%d max_tokens=%d temperature=%s retries=%d",
            request_id,
            self.provider,
            self.model,
            prompt_chars,
            max_tokens,
            temperature,
            retries,
        )

        attempt = 0
        while attempt < retries:
            started_at = time.perf_counter()
            try:
                if self.provider in ("openai", "groq", "ollama"):
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs
                    )
                    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
                    finish_reason = None
                    if response.choices:
                        finish_reason = response.choices[0].finish_reason
                    logger.info(
                        "LLM request success id=%s attempt=%d latency_ms=%d finish_reason=%s",
                        request_id,
                        attempt + 1,
                        elapsed_ms,
                        finish_reason,
                    )
                    content = response.choices[0].message.content
                    if content:
                        logger.info("LLM response content id=%s len=%d content=%s", request_id, len(content), content[:200])
                    else:
                        logger.warning("LLM response content is empty/null id=%s", request_id)
                    return content
            except Exception as e:
                error_text = str(e)
                is_rate_limit = "rate_limit_exceeded" in error_text or "Error code: 429" in error_text
                attempt += 1
                elapsed_ms = int((time.perf_counter() - started_at) * 1000)
                error_code = getattr(e, "code", None)
                error_type = getattr(e, "type", None)
                status_code = getattr(e, "status_code", None)

                logger.warning(
                    "LLM request failed id=%s attempt=%d latency_ms=%d status=%s code=%s type=%s rate_limit=%s error=%s",
                    request_id,
                    attempt,
                    elapsed_ms,
                    status_code,
                    error_code,
                    error_type,
                    is_rate_limit,
                    error_text,
                )

                if is_rate_limit and attempt < retries:
                    sleep_for = retry_delay_seconds * attempt
                    logger.warning(
                        "Rate limit retry scheduled id=%s model=%s sleep=%.1fs attempt=%d/%d",
                        request_id,
                        self.model,
                        sleep_for,
                        attempt,
                        retries,
                    )
                    time.sleep(sleep_for)
                    continue

                logger.error("LLM request failed permanently id=%s", request_id)
                return None

        return None
    
    @staticmethod
    def _extract_json_candidate(text: str) -> Optional[str]:
        """Extract likely JSON object payload from model output text."""
        if not text:
            return None

        stripped = text.strip()

        # Common case: fenced markdown block
        fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", stripped, re.IGNORECASE)
        if fenced:
            return fenced.group(1)

        # Fallback: first JSON object-like span
        object_like = re.search(r"\{[\s\S]*\}", stripped)
        if object_like:
            return object_like.group(0)

        return None

    @staticmethod
    def _try_close_truncated_json_object(candidate: str) -> str:
        """Best-effort close for truncated JSON with unbalanced brackets/braces."""
        if not candidate:
            return candidate

        in_string = False
        escape = False
        brace_balance = 0
        bracket_balance = 0

        for ch in candidate:
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
            elif ch == "{":
                brace_balance += 1
            elif ch == "}":
                brace_balance -= 1
            elif ch == "[":
                bracket_balance += 1
            elif ch == "]":
                bracket_balance -= 1

        repaired = candidate
        if in_string:
            repaired += '"'

        if bracket_balance > 0:
            repaired += "]" * bracket_balance
        if brace_balance > 0:
            repaired += "}" * brace_balance

        return repaired

    def parse_json_response(
        self,
        prompt: str,
        temperature: float = 0.0,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Generate and parse JSON response from LLM
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            **kwargs: Additional parameters
            
        Returns:
            Parsed JSON object or None if error
        """
        import json
        
        response = self.generate(
            prompt,
            temperature=temperature,
            **kwargs
        )
        
        if response:
            try:
                return json.loads(response)
            except json.JSONDecodeError as e:
                candidate = self._extract_json_candidate(response)
                if candidate:
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        repaired = self._try_close_truncated_json_object(candidate)
                        try:
                            parsed = json.loads(repaired)
                            logger.warning("Recovered JSON from truncated/wrapped model output")
                            return parsed
                        except json.JSONDecodeError:
                            pass

                logger.error(
                    "Failed to parse LLM response as JSON. error=%s response_prefix=%s",
                    e,
                    response[:500],
                )
                return None
        else:
            logger.warning("LLM generate() returned None/empty response")
            return None


# Global LLM client instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create global LLM client instance"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
