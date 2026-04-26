"""
Resolvers for the baseline-trace-domain structured logs.
"""

from .page_errors_log import (
    ResolvedPageErrorsLog,
    page_errors_log_path,
    resolve_page_errors_log,
)

__all__ = [
    "ResolvedPageErrorsLog",
    "page_errors_log_path",
    "resolve_page_errors_log",
]
