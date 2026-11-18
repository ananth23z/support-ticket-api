"""
app/core/logging_config.py
==========================
WHAT:  Configures Python's built-in `logging` module once for the whole app.
WHY:   `print()` is fine for experiments, but real apps use logging because it has
       levels (DEBUG/INFO/WARNING/ERROR), timestamps, and can be sent to files or
       monitoring tools without changing the code that writes the logs.

ASP.NET ANALOGY:
    Like `builder.Logging.AddConsole()` + injecting `ILogger<T>`.
    In Python you get a logger with `logging.getLogger("some.name")`.

WHO USES IT:
    - main.py calls setup_logging() at startup
    - middleware/logging_middleware.py and services write log lines
"""

import logging


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,  # show INFO and above (INFO, WARNING, ERROR, CRITICAL)
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
