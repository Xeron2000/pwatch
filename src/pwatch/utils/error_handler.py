"""
Error handling utilities for PriceSentry system.
Provides unified error handling, retry mechanisms, and circuit breaker patterns.
"""

import asyncio
import functools
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ErrorSeverity(Enum):
    """Error severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for better classification."""

    NETWORK = "network"
    API = "api"
    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Structured error information."""

    error_code: str
    error_message: str
    error_category: ErrorCategory
    severity: ErrorSeverity
    timestamp: datetime
    context: Dict[str, Any]
    retry_count: int = 0
    original_error: Optional[Exception] = None


class CircuitBreaker:
    """Circuit breaker implementation for preventing cascading failures."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.logger = logging.getLogger(__name__)

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                self.logger.info("Circuit breaker attempting reset")
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset."""
        if self.last_failure_time is None:
            return True

        time_diff = (datetime.now() - self.last_failure_time).total_seconds()
        should_reset = time_diff >= self.recovery_timeout
        self.logger.debug((f"Time diff: {time_diff}, timeout: {self.recovery_timeout}, should reset: {should_reset}"))
        return should_reset

    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.logger.info("Circuit breaker reset to closed state")

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            if self.state == "CLOSED":
                self.state = "OPEN"
                self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
            elif self.state == "HALF_OPEN":
                self.state = "OPEN"
                self.logger.warning("Circuit breaker re-opened after failure in half-open state")


class ErrorHandler:
    """Unified error handling system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_history: List[ErrorInfo] = []
        self.max_history_size = 1000

    def retry_with_backoff(
        self,
        func: Optional[Callable] = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        retryable_exceptions: tuple = (Exception,),
    ) -> Any:
        """Retry function with exponential backoff."""

        def decorator(f: Callable) -> Callable:
            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                return self._retry_with_backoff_impl(
                    f,
                    max_retries,
                    base_delay,
                    max_delay,
                    backoff_factor,
                    retryable_exceptions,
                    *args,
                    **kwargs,
                )

            return wrapper

        if func is None:
            return decorator
        else:
            return decorator(func)

    def _retry_with_backoff_impl(
        self,
        func,
        max_retries,
        base_delay,
        max_delay,
        backoff_factor,
        retryable_exceptions,
        *args,
        **kwargs,
    ):
        """Implementation of retry with exponential backoff."""
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except retryable_exceptions as e:
                last_exception = e

                if attempt == max_retries:
                    func_name = getattr(func, "__name__", "unknown_function")
                    self._log_error(
                        error_code="RETRY_EXHAUSTED",
                        error_message=f"Retry attempts exhausted for {func_name}",
                        error_category=ErrorCategory.NETWORK,
                        severity=ErrorSeverity.ERROR,
                        context={"function": func_name, "attempts": attempt + 1},
                        original_error=e,
                    )
                    raise

                # Calculate delay with exponential backoff
                delay = min(base_delay * (backoff_factor**attempt), max_delay)

                func_name = getattr(func, "__name__", "unknown_function")
                self._log_error(
                    error_code="RETRY_ATTEMPT",
                    error_message=(f"Retry attempt {attempt + 1}/{max_retries} for {func_name}"),
                    error_category=ErrorCategory.NETWORK,
                    severity=ErrorSeverity.WARNING,
                    context={
                        "function": func_name,
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "delay": delay,
                    },
                    original_error=e,
                )

                time.sleep(delay)

        raise last_exception

    async def retry_with_backoff_async(
        self,
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        retryable_exceptions: tuple = (Exception,),
    ) -> Any:
        """Async retry function with exponential backoff."""
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return await func()
            except retryable_exceptions as e:
                last_exception = e

                if attempt == max_retries:
                    func_name = getattr(func, "__name__", "unknown_function")
                    self._log_error(
                        error_code="RETRY_EXHAUSTED_ASYNC",
                        error_message=f"Async retry attempts exhausted for {func_name}",
                        error_category=ErrorCategory.NETWORK,
                        severity=ErrorSeverity.ERROR,
                        context={"function": func_name, "attempts": attempt + 1},
                        original_error=e,
                    )
                    raise

                # Calculate delay with exponential backoff
                delay = min(base_delay * (backoff_factor**attempt), max_delay)

                func_name = getattr(func, "__name__", "unknown_function")
                self._log_error(
                    error_code="RETRY_ATTEMPT_ASYNC",
                    error_message=(f"Async retry attempt {attempt + 1}/{max_retries} for {func_name}"),
                    error_category=ErrorCategory.NETWORK,
                    severity=ErrorSeverity.WARNING,
                    context={
                        "function": func_name,
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "delay": delay,
                    },
                    original_error=e,
                )

                await asyncio.sleep(delay)

        raise last_exception

    def circuit_breaker_protect(
        self, circuit_name: str, failure_threshold: int = 5, recovery_timeout: int = 60
    ) -> Callable:
        """Decorator for circuit breaker protection."""

        if circuit_name not in self.circuit_breakers:
            self.circuit_breakers[circuit_name] = CircuitBreaker(
                failure_threshold=failure_threshold, recovery_timeout=recovery_timeout
            )

        circuit_breaker = self.circuit_breakers[circuit_name]

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return circuit_breaker.call(func, *args, **kwargs)

            return wrapper

        return decorator

    def handle_api_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        severity: ErrorSeverity = ErrorSeverity.ERROR,
    ) -> ErrorInfo:
        """Handle API errors with structured logging."""

        error_category = ErrorCategory.API
        error_code = "API_ERROR"

        # Classify specific API errors
        if "timeout" in str(error).lower():
            error_code = "API_TIMEOUT"
        elif "429" in str(error) or "rate" in str(error).lower():
            error_code = "API_RATE_LIMIT"
        elif "401" in str(error) or "unauthorized" in str(error).lower():
            error_code = "API_UNAUTHORIZED"
        elif "404" in str(error) or "not found" in str(error).lower():
            error_code = "API_NOT_FOUND"
        elif "500" in str(error):
            error_code = "API_SERVER_ERROR"

        return self._log_error(
            error_code=error_code,
            error_message=str(error),
            error_category=error_category,
            severity=severity,
            context=context,
            original_error=error,
        )

    def handle_network_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        severity: ErrorSeverity = ErrorSeverity.WARNING,
    ) -> ErrorInfo:
        """Handle network errors with structured logging."""

        error_category = ErrorCategory.NETWORK
        error_code = "NETWORK_ERROR"

        # Classify specific network errors
        if "connection" in str(error).lower():
            error_code = "NETWORK_CONNECTION"
        elif "resolve" in str(error).lower():
            error_code = "NETWORK_DNS"
        elif "timeout" in str(error).lower():
            error_code = "NETWORK_TIMEOUT"
        elif "ssl" in str(error).lower() or "certificate" in str(error).lower():
            error_code = "NETWORK_SSL"

        return self._log_error(
            error_code=error_code,
            error_message=str(error),
            error_category=error_category,
            severity=severity,
            context=context,
            original_error=error,
        )

    def handle_config_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        severity: ErrorSeverity = ErrorSeverity.ERROR,
    ) -> ErrorInfo:
        """Handle configuration errors with structured logging."""

        error_category = ErrorCategory.CONFIGURATION
        error_code = "CONFIG_ERROR"

        return self._log_error(
            error_code=error_code,
            error_message=str(error),
            error_category=error_category,
            severity=severity,
            context=context,
            original_error=error,
        )

    def _log_error(
        self,
        error_code: str,
        error_message: str,
        error_category: ErrorCategory,
        severity: ErrorSeverity,
        context: Dict[str, Any],
        original_error: Optional[Exception] = None,
    ) -> ErrorInfo:
        """Log error with structured information."""

        error_info = ErrorInfo(
            error_code=error_code,
            error_message=error_message,
            error_category=error_category,
            severity=severity,
            timestamp=datetime.now(),
            context=context,
            original_error=original_error,
        )

        # Add to error history
        self.error_history.append(error_info)

        # Trim history if needed
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size :]

        # Log based on severity
        log_message = f"[{error_code}] {error_message} | Context: {context}"

        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, exc_info=original_error)
        elif severity == ErrorSeverity.ERROR:
            self.logger.error(log_message, exc_info=original_error)
        elif severity == ErrorSeverity.WARNING:
            self.logger.warning(log_message, exc_info=original_error)
        else:
            self.logger.info(log_message, exc_info=original_error)

        return error_info

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        if not self.error_history:
            return {"total_errors": 0}

        # Group errors by category
        category_counts = {}
        severity_counts = {}
        code_counts = {}

        for error in self.error_history:
            category = error.error_category.value
            severity = error.severity.value
            code = error.error_code

            category_counts[category] = category_counts.get(category, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            code_counts[code] = code_counts.get(code, 0) + 1

        # Calculate recent errors (last hour)
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_errors = [error for error in self.error_history if error.timestamp > one_hour_ago]

        return {
            "total_errors": len(self.error_history),
            "recent_errors": len(recent_errors),
            "by_category": category_counts,
            "by_severity": severity_counts,
            "by_code": code_counts,
            "circuit_breakers": {
                name: {
                    "state": cb.state,
                    "failure_count": cb.failure_count,
                    "last_failure": cb.last_failure_time.isoformat() if cb.last_failure_time else None,
                }
                for name, cb in self.circuit_breakers.items()
            },
        }

    def clear_error_history(self):
        """Clear error history."""
        self.error_history.clear()
        self.logger.info("Error history cleared")

    def reset_circuit_breakers(self):
        """Reset all circuit breakers."""
        for circuit_breaker in self.circuit_breakers.values():
            circuit_breaker.failure_count = 0
            circuit_breaker.state = "closed"
            circuit_breaker.last_failure_time = None

        self.logger.info("All circuit breakers reset")


# Global error handler instance
error_handler = ErrorHandler()
