"""Utility module to display a busy indicator."""

import itertools
import sys
import threading
from collections.abc import Generator
from contextlib import contextmanager


enabled = True
"""Global flag to enable/disable the busy indicators."""


def _spinning_cursor_thread(
    message: str,
    finish_event: threading.Event,
    period: float = 1.0,
    file=sys.stderr,
):
    cursor_sequence = '|/-\\'
    wait_time = period / len(cursor_sequence)
    prefix = f'{message} ... '
    file.write(prefix)
    for cursor in itertools.cycle(cursor_sequence):
        file.write(cursor)
        file.flush()
        if finish_event.wait(timeout=wait_time):
            if file.writable():
                file.write('\bdone\n')
                file.flush()
            break
        file.write('\b')


@contextmanager
def spinning_cursor(message: str, period: float = 1.0, file=sys.stderr) -> Generator[None, None, None]:
    """
    A context manager which displays a spinning cursor to the screen while the computation inside the context executes.

    The intended use of this context manager is to display feedback to the user of a program while a long-running
    computation executes. Developers must specify a message to explain what computation is executing, and they can also
    specify the rate at which the cursor spins and the output file for the cursor.

    Example use in a `with`-statement::

        >>> import time
        >>> with spinning_cursor('Sleeping'):
        ...     time.sleep(5)

    Example use as a decorator::

        >>> import pandas as pd
        >>> @spinning_cursor('Downloading database')
        ... def fetch_database() -> pd.DataFrame:
        ...     ...

    :param message: Message to display to the screen.
    :param period: Duration in seconds of each half rotation of the cursor (default: 1 second).
    :param file: File to write the cursor to (default: sys.stderr).
    """
    if enabled:
        finish_event: threading.Event | None = None
        thread: threading.Thread | None = None
        try:
            finish_event = threading.Event()
            thread = threading.Thread(target=_spinning_cursor_thread, args=(message, finish_event, period, file))
            thread.start()
            yield
        finally:
            if finish_event is not None:
                finish_event.set()
            if thread is not None:
                thread.join()
    else:
        yield
