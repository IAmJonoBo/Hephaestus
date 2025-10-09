"""OpenTelemetry tracing utilities for CLI commands (ADR-0003 Sprint 2).

This module provides decorators and context managers for instrumenting
CLI commands with distributed tracing spans.
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, TypeVar

from hephaestus.telemetry import get_tracer, is_telemetry_enabled

__all__ = [
    "trace_command",
    "trace_operation",
]

T = TypeVar("T")


def trace_command(command_name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to trace a CLI command with OpenTelemetry.

    Args:
        command_name: Name of the command (e.g., "guard-rails", "cleanup")

    Returns:
        Decorated function with tracing

    Example:
        @trace_command("guard-rails")
        def guard_rails(no_format: bool = False) -> None:
            # Command implementation
            pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            if not is_telemetry_enabled():
                return func(*args, **kwargs)

            tracer = get_tracer(__name__)

            with tracer.start_as_current_span(f"cli.{command_name}") as span:
                # Add command attributes
                span.set_attribute("command.name", command_name)
                span.set_attribute("command.args", str(kwargs))

                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("command.success", True)
                    return result
                except Exception as exc:
                    span.set_attribute("command.success", False)
                    span.set_attribute("command.error", str(exc))
                    span.add_event(
                        "command.failed",
                        attributes={
                            "error.type": type(exc).__name__,
                            "error.message": str(exc),
                        },
                    )
                    raise
                finally:
                    duration = time.time() - start_time
                    span.set_attribute("command.duration_ms", duration * 1000)

        return wrapper

    return decorator


@contextmanager
def trace_operation(
    operation_name: str,
    **attributes: Any,
) -> Iterator[Any]:
    """Context manager to trace an operation within a command.

    Args:
        operation_name: Name of the operation (e.g., "cleanup", "lint", "test")
        **attributes: Additional attributes to attach to the span

    Yields:
        Span object (or no-op if telemetry disabled)

    Example:
        with trace_operation("cleanup", deep_clean=True):
            # Cleanup implementation
            pass
    """
    if not is_telemetry_enabled():
        yield None
        return

    tracer = get_tracer(__name__)

    with tracer.start_as_current_span(operation_name) as span:
        # Add operation attributes
        for key, value in attributes.items():
            span.set_attribute(f"operation.{key}", value)

        start_time = time.time()
        try:
            yield span
        except Exception as exc:
            span.set_attribute("operation.success", False)
            span.set_attribute("operation.error", str(exc))
            span.add_event(
                "operation.failed",
                attributes={
                    "error.type": type(exc).__name__,
                    "error.message": str(exc),
                },
            )
            raise
        else:
            span.set_attribute("operation.success", True)
        finally:
            duration = time.time() - start_time
            span.set_attribute("operation.duration_ms", duration * 1000)
