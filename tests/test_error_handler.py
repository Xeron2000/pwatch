"""
Test cases for error handling system.
"""

import time
from unittest.mock import Mock, patch

import pytest

from pwatch.utils.error_handler import (
    CircuitBreaker,
    ErrorCategory,
    ErrorHandler,
    ErrorInfo,
    ErrorSeverity,
)


class TestErrorHandler:
    """Test error handling functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.error_handler = ErrorHandler()

    def test_init(self):
        """Test ErrorHandler initialization."""
        assert self.error_handler.max_history_size == 1000
        assert len(self.error_handler.error_history) == 0
        assert len(self.error_handler.circuit_breakers) == 0

    def test_log_error(self):
        """Test error logging functionality."""
        error = Exception("Test error")
        context = {"component": "test", "operation": "test_operation"}

        error_info = self.error_handler._log_error(
            error_code="TEST_ERROR",
            error_message="Test error message",
            error_category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.ERROR,
            context=context,
            original_error=error,
        )

        assert isinstance(error_info, ErrorInfo)
        assert error_info.error_code == "TEST_ERROR"
        assert error_info.error_message == "Test error message"
        assert error_info.error_category == ErrorCategory.SYSTEM
        assert error_info.severity == ErrorSeverity.ERROR
        assert error_info.context == context
        assert error_info.original_error == error

        # Check if error was added to history
        assert len(self.error_handler.error_history) == 1
        assert self.error_handler.error_history[0] == error_info

    def test_log_error_with_retry_count(self):
        """Test error logging with retry count."""
        error_info = self.error_handler._log_error(
            error_code="RETRY_ERROR",
            error_message="Retry error",
            error_category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.WARNING,
            context={},
        )

        # Note: retry_count is not a parameter in _log_error method
        # It's set to 0 by default in ErrorInfo dataclass
        assert error_info.retry_count == 0

    def test_retry_with_backoff_success(self):
        """Test retry with backoff on successful execution."""
        mock_func = Mock(return_value="success")

        result = self.error_handler.retry_with_backoff(
            mock_func, max_retries=3, base_delay=0.1
        )()

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_with_backoff_with_exception_then_success(self):
        """Test retry with backoff when function fails then succeeds."""
        mock_func = Mock(side_effect=[Exception("First failure"), "success"])

        with patch("time.sleep"):  # Mock sleep to speed up test
            result = self.error_handler.retry_with_backoff(
                mock_func, max_retries=3, base_delay=0.1
            )()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_retry_with_backoff_exhausted_retries(self):
        """Test retry with backoff when all retries are exhausted."""
        mock_func = Mock(side_effect=Exception("Persistent failure"))

        with patch("time.sleep"):  # Mock sleep to speed up test
            with pytest.raises(Exception, match="Persistent failure"):
                self.error_handler.retry_with_backoff(
                    mock_func, max_retries=3, base_delay=0.1
                )()

        assert mock_func.call_count == 4  # 1 initial + 3 retries

    def test_retry_with_backoff_decorator(self):
        """Test retry with backoff as decorator."""

        @self.error_handler.retry_with_backoff(max_retries=2, base_delay=0.1)
        def test_function():
            if not hasattr(test_function, "call_count"):
                test_function.call_count = 0
            test_function.call_count += 1
            if test_function.call_count < 2:
                raise Exception("Test failure")
            return "success"

        with patch("time.sleep"):  # Mock sleep to speed up test
            result = test_function()

        assert result == "success"
        assert test_function.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_with_backoff_async_success(self):
        """Test async retry with backoff on successful execution."""

        async def mock_func():
            return "success"

        with patch("asyncio.sleep"):  # Mock sleep to speed up test
            result = await self.error_handler.retry_with_backoff_async(
                mock_func, max_retries=3, base_delay=0.1
            )

        assert result == "success"

    @pytest.mark.asyncio
    async def test_retry_with_backoff_async_with_exception_then_success(self):
        """Test async retry with backoff when function fails then succeeds."""

        call_count = 0

        async def mock_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First failure")
            return "success"

        with patch("asyncio.sleep"):  # Mock sleep to speed up test
            result = await self.error_handler.retry_with_backoff_async(
                mock_func, max_retries=3, base_delay=0.1
            )

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_with_backoff_async_exhausted_retries(self):
        """Test async retry with backoff when all retries are exhausted."""

        call_count = 0

        async def mock_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Persistent failure")

        with patch("asyncio.sleep"):  # Mock sleep to speed up test
            with pytest.raises(Exception, match="Persistent failure"):
                await self.error_handler.retry_with_backoff_async(
                    mock_func, max_retries=3, base_delay=0.1
                )

        assert call_count == 4  # 1 initial + 3 retries

    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker initial state."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 60
        assert cb.failure_count == 0
        assert cb.last_failure_time is None
        assert cb.state == "CLOSED"  # Uppercase in implementation

    def test_circuit_breaker_success_call(self):
        """Test circuit breaker with successful call."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        mock_func = Mock(return_value="success")

        result = cb.call(mock_func)

        assert result == "success"
        assert cb.failure_count == 0
        assert cb.state == "CLOSED"

    def test_circuit_breaker_failure_under_threshold(self):
        """Test circuit breaker with failures under threshold."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        mock_func = Mock(side_effect=Exception("Failure"))

        for i in range(2):
            with pytest.raises(Exception, match="Failure"):
                cb.call(mock_func)

        assert cb.failure_count == 2
        assert cb.state == "CLOSED"

    def test_circuit_breaker_failure_over_threshold(self):
        """Test circuit breaker with failures over threshold."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        mock_func = Mock(side_effect=Exception("Failure"))

        # Trigger failures to open circuit
        for i in range(3):
            with pytest.raises(Exception, match="Failure"):
                cb.call(mock_func)

        assert cb.failure_count == 3
        assert cb.state == "OPEN"  # lowercase in implementation

        # Next call should raise CircuitBreakerOpenError
        with pytest.raises(Exception):
            cb.call(mock_func)

    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
        mock_func = Mock(side_effect=Exception("Failure"))

        # Trigger failures to open circuit
        for i in range(3):
            with pytest.raises(Exception, match="Failure"):
                cb.call(mock_func)

        assert cb.state == "OPEN"

        # Wait for recovery timeout
        time.sleep(0.2)

        # Next call should be attempted (half-open state)
        with pytest.raises(Exception, match="Failure"):
            cb.call(mock_func)

        # Should still be open due to failure
        assert cb.state == "OPEN"

    def test_circuit_breaker_recovery_success(self):
        """Test circuit breaker recovery with successful call."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)

        # Function that fails initially, then succeeds
        def failing_then_succeeding():
            if not hasattr(failing_then_succeeding, "call_count"):
                failing_then_succeeding.call_count = 0
            failing_then_succeeding.call_count += 1
            if failing_then_succeeding.call_count <= 3:
                raise Exception("Failure")
            return "success"

        # Trigger failures to open circuit
        for i in range(3):
            with pytest.raises(Exception, match="Failure"):
                cb.call(failing_then_succeeding)

        assert cb.state == "OPEN"

        # Wait for recovery timeout
        time.sleep(0.2)

        # Next call should succeed and close circuit
        result = cb.call(failing_then_succeeding)
        assert result == "success"
        assert cb.failure_count == 0
        assert cb.state == "CLOSED"

    def test_circuit_breaker_protect_decorator(self):
        """Test circuit breaker protect decorator."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        self.error_handler.circuit_breakers["test_circuit"] = cb

        @self.error_handler.circuit_breaker_protect("test_circuit")
        def test_function():
            if not hasattr(test_function, "call_count"):
                test_function.call_count = 0
            test_function.call_count += 1
            if test_function.call_count <= 2:
                raise Exception("Failure")
            return "success"

        # Trigger failures to open circuit
        for i in range(2):
            with pytest.raises(Exception, match="Failure"):
                test_function()

        # Circuit should be open now
        assert cb.state == "OPEN"

        # Next call should raise CircuitBreakerOpenError
        with pytest.raises(Exception):
            test_function()

    def test_handle_api_error(self):
        """Test API error handling."""
        error = Exception("API Error")
        context = {"endpoint": "/api/test", "method": "GET"}

        error_info = self.error_handler.handle_api_error(error, context)

        assert isinstance(error_info, ErrorInfo)
        assert error_info.error_category == ErrorCategory.API
        assert error_info.severity == ErrorSeverity.ERROR
        assert error_info.context == context
        assert error_info.original_error == error

    def test_handle_network_error(self):
        """Test network error handling."""
        error = Exception("Network Error")
        context = {"host": "api.example.com", "port": 443}

        error_info = self.error_handler.handle_network_error(
            error, context, ErrorSeverity.ERROR
        )

        assert isinstance(error_info, ErrorInfo)
        assert error_info.error_category == ErrorCategory.NETWORK
        assert error_info.severity == ErrorSeverity.ERROR
        assert error_info.context == context

    def test_handle_config_error(self):
        """Test configuration error handling."""
        error = Exception("Config Error")
        context = {"config_file": "config.yaml", "section": "database"}

        error_info = self.error_handler.handle_config_error(
            error, context, ErrorSeverity.CRITICAL
        )

        assert isinstance(error_info, ErrorInfo)
        assert error_info.error_category == ErrorCategory.CONFIGURATION
        assert error_info.severity == ErrorSeverity.CRITICAL
        assert error_info.context == context

    def test_error_history_limit(self):
        """Test error history size limit."""
        self.error_handler.max_history_size = 3

        # Add more errors than the limit
        for i in range(5):
            self.error_handler._log_error(
                error_code=f"ERROR_{i}",
                error_message=f"Error {i}",
                error_category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.ERROR,
                context={},
            )

        # Should only keep the most recent errors
        assert len(self.error_handler.error_history) == 3
        assert self.error_handler.error_history[-1].error_code == "ERROR_4"

    def test_get_error_stats(self):
        """Test error statistics generation."""
        # Add various errors
        self.error_handler._log_error(
            error_code="API_ERROR",
            error_message="API Error",
            error_category=ErrorCategory.API,
            severity=ErrorSeverity.ERROR,
            context={},
        )

        self.error_handler._log_error(
            error_code="NETWORK_ERROR",
            error_message="Network Error",
            error_category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.WARNING,
            context={},
        )

        self.error_handler._log_error(
            error_code="ANOTHER_API_ERROR",
            error_message="Another API Error",
            error_category=ErrorCategory.API,
            severity=ErrorSeverity.ERROR,
            context={},
        )

        stats = self.error_handler.get_error_stats()

        assert stats["total_errors"] == 3
        assert stats["by_category"]["api"] == 2
        assert stats["by_category"]["network"] == 1
        assert stats["by_severity"]["error"] == 2
        assert stats["by_severity"]["warning"] == 1
