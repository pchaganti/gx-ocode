"""Centralized timeout handling utilities for reliable tool execution."""

import asyncio
import functools
import signal
import threading
from contextlib import contextmanager
from typing import Any, Callable, List, Optional, TypeVar, Union

T = TypeVar("T")


class TimeoutError(Exception):
    """Enhanced timeout error with context information."""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        duration: Optional[float] = None,
        context: Optional[dict] = None,
    ):
        """Initialize TimeoutError with detailed context.

        Args:
            message: Base error message.
            operation: Name of the operation that timed out.
            duration: Timeout duration in seconds.
            context: Additional context information as dictionary.
        """
        self.operation = operation
        self.duration = duration
        self.context = context or {}

        detailed_message = message
        if operation:
            detailed_message += f" (Operation: {operation})"
        if duration:
            detailed_message += f" (Timeout: {duration}s)"
        if context:
            detailed_message += f" (Context: {context})"

        super().__init__(detailed_message)


def async_timeout(
    seconds: float,
    operation: Optional[str] = None,
    cleanup: Optional[Callable[[], Any]] = None,
):
    """
    Async context manager for operations with timeout.

    Args:
        seconds: Timeout duration in seconds
        operation: Optional operation name for better error messages
        cleanup: Optional cleanup function to call on timeout

    Example:
        async with async_timeout(5.0, "file_read"):
            data = await read_large_file()
    """

    class TimeoutContext:
        """Async context manager for timeout handling.

        Manages timeout scheduling and cancellation for async operations.
        """

        def __init__(self):
            """Initialize timeout context."""
            self.timeout_handle = None
            self.timed_out = False

        async def __aenter__(self):
            """Enter async context and set up timeout.

            Returns:
                Self for context manager usage.
            """
            loop = asyncio.get_event_loop()

            def timeout_callback():
                """Handle timeout expiration and run cleanup."""
                self.timed_out = True
                if cleanup:
                    try:
                        if asyncio.iscoroutinefunction(cleanup):
                            asyncio.create_task(cleanup())
                        else:
                            cleanup()
                    except Exception:
                        pass  # Best effort cleanup  # nosec B110

            self.timeout_handle = loop.call_later(seconds, timeout_callback)
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            """Exit async context and handle timeout.

            Args:
                exc_type: Exception type if raised.
                exc_val: Exception value if raised.
                exc_tb: Exception traceback if raised.

            Raises:
                TimeoutError: If operation timed out.
            """
            if self.timeout_handle:
                self.timeout_handle.cancel()

            if self.timed_out and exc_type is None:
                raise TimeoutError(
                    f"Operation timed out after {seconds} seconds",
                    operation=operation,
                    duration=seconds,
                )

            return False

    return TimeoutContext()


def sync_timeout(seconds: float, operation: Optional[str] = None):
    """
    Decorator for synchronous functions with timeout using threading.

    Args:
        seconds: Timeout duration in seconds
        operation: Optional operation name for better error messages

    Example:
        @sync_timeout(5.0, "network_request")
        def fetch_data():
            return requests.get(url)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        """Decorator that adds timeout to a function.

        Args:
            func: Function to wrap with timeout.

        Returns:
            Wrapped function with timeout capability.
        """

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            """Execute function with timeout.

            Args:
                *args: Positional arguments for wrapped function.
                **kwargs: Keyword arguments for wrapped function.

            Returns:
                Result from wrapped function.

            Raises:
                TimeoutError: If function execution exceeds timeout.
            """
            result: List[Optional[T]] = [None]
            exception: List[Optional[Exception]] = [None]

            def target():
                """Target function for thread execution."""
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout=seconds)

            if thread.is_alive():
                # Thread is still running, we've timed out
                raise TimeoutError(
                    f"Function '{func.__name__}' timed out after {seconds} seconds",
                    operation=operation or func.__name__,
                    duration=seconds,
                )

            if exception[0]:
                raise exception[0]

            if result[0] is None:
                raise ValueError("Function returned None")
            return result[0]

        return wrapper

    return decorator


@contextmanager
def signal_timeout(seconds: float, operation: Optional[str] = None):
    """
    Context manager using signal-based timeout (Unix only).

    Args:
        seconds: Timeout duration in seconds
        operation: Optional operation name for better error messages

    Example:
        with signal_timeout(5.0, "file_operation"):
            process_large_file()
    """

    def timeout_handler(signum, frame):
        """Signal handler for timeout.

        Args:
            signum: Signal number received.
            frame: Current stack frame.

        Raises:
            TimeoutError: Always raises to indicate timeout.
        """
        raise TimeoutError(
            f"Operation timed out after {seconds} seconds",
            operation=operation,
            duration=seconds,
        )

    # Set up signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(int(seconds))

    try:
        yield
    finally:
        # Restore original handler and cancel alarm
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


async def with_timeout(
    coro,
    timeout: float,
    operation: Optional[str] = None,
    default: Optional[T] = None,
    raise_on_timeout: bool = True,
) -> Union[T, Any]:
    """
    Execute a coroutine with timeout and optional default value.

    Args:
        coro: Coroutine to execute
        timeout: Timeout in seconds
        operation: Optional operation name for error context
        default: Default value to return on timeout (if not raising)
        raise_on_timeout: Whether to raise TimeoutError or return default

    Returns:
        Result of coroutine or default value on timeout

    Example:
        result = await with_timeout(
            fetch_data(),
            timeout=5.0,
            operation="data_fetch",
            default=[]
        )
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        if raise_on_timeout:
            raise TimeoutError(
                f"Coroutine timed out after {timeout} seconds",
                operation=operation,
                duration=timeout,
            )
        return default


class TimeoutManager:
    """
    Manages cascading timeouts for complex operations.

    Example:
        tm = TimeoutManager(total_timeout=30.0)

        async with tm.operation("fetch", 10.0):
            data = await fetch_data()

        async with tm.operation("process", 15.0):
            result = await process_data(data)
    """

    def __init__(self, total_timeout: float):
        """Initialize timeout manager with total timeout budget.

        Args:
            total_timeout: Total timeout in seconds for all operations.
        """
        self.total_timeout = total_timeout
        self.start_time = asyncio.get_event_loop().time()
        self.operations: List[dict] = []

    def remaining_time(self) -> float:
        """Get remaining time from total timeout."""
        elapsed = asyncio.get_event_loop().time() - self.start_time
        return max(0, self.total_timeout - elapsed)

    def operation(self, name: str, timeout: Optional[float] = None):
        """
        Create a timeout context for an operation.

        Args:
            name: Operation name
            timeout: Operation timeout (uses remaining time if None)
        """
        remaining = self.remaining_time()
        if remaining <= 0:
            raise TimeoutError(
                "Total timeout exceeded",
                operation=f"manager({name})",
                duration=self.total_timeout,
                context={"operations": self.operations},
            )

        op_timeout = min(timeout or remaining, remaining)
        self.operations.append({"name": name, "timeout": op_timeout})

        return async_timeout(op_timeout, operation=name)


class AdaptiveTimeout:
    """
    Adaptive timeout that adjusts based on operation history.

    Useful for operations with variable completion times.
    """

    def __init__(
        self,
        base_timeout: float,
        min_timeout: float = 1.0,
        max_timeout: float = 300.0,
        adjustment_factor: float = 1.5,
    ):
        """Initialize adaptive timeout manager.

        Args:
            base_timeout: Initial timeout value in seconds.
            min_timeout: Minimum allowed timeout.
            max_timeout: Maximum allowed timeout.
            adjustment_factor: Multiplier for average duration to calculate timeout.
        """
        self.base_timeout = base_timeout
        self.min_timeout = min_timeout
        self.max_timeout = max_timeout
        self.adjustment_factor = adjustment_factor
        self.history: List[float] = []
        self.current_timeout = base_timeout

    def record_duration(self, duration: float):
        """Record actual operation duration."""
        self.history.append(duration)
        # Keep only recent history
        if len(self.history) > 10:
            self.history.pop(0)

        # Adjust timeout based on history
        if self.history:
            avg_duration = sum(self.history) / len(self.history)
            self.current_timeout = min(
                max(avg_duration * self.adjustment_factor, self.min_timeout),
                self.max_timeout,
            )

    def get_timeout(self) -> float:
        """Get current adaptive timeout value."""
        return self.current_timeout

    async def execute(self, coro, operation: Optional[str] = None) -> Any:
        """Execute coroutine with adaptive timeout."""
        start_time = asyncio.get_event_loop().time()
        try:
            result: Any = await with_timeout(
                coro, timeout=self.current_timeout, operation=operation
            )
            duration = asyncio.get_event_loop().time() - start_time
            self.record_duration(duration)
            return result
        except TimeoutError:
            # Increase timeout for next attempt
            self.current_timeout = min(
                self.current_timeout * self.adjustment_factor, self.max_timeout
            )
            raise
