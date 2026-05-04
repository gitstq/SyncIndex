"""
File system watcher for SyncIndex.

Implements polling-based file system monitoring that detects changes
and triggers synchronization automatically.
"""

import os
import sys
import time
import threading

from .indexer import Indexer
from .sync_engine import SyncEngine
from .utils import (
    colored,
    Colors,
    format_duration,
    info,
    warning,
    error,
)


class WatchEvent:
    """Represents a file system change event.

    Attributes:
        event_type: One of ``"created"``, ``"modified"``, ``"deleted"``.
        path: The file path that changed.
        source: Name of the data source.
        timestamp: When the event was detected (Unix timestamp).
    """

    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"

    def __init__(self, event_type, path, source="unknown", timestamp=None):
        """Initialize a watch event.

        Args:
            event_type: Type of change (``created``, ``modified``, ``deleted``).
            path: File path that changed.
            source: Data source name.
            timestamp: Detection time (defaults to now).
        """
        self.event_type = event_type
        self.path = path
        self.source = source
        self.timestamp = timestamp or time.time()

    def __repr__(self):
        return f"WatchEvent({self.event_type}, '{self.path}', source='{self.source}')"


class Watcher:
    """Polling-based file system watcher.

    Periodically scans registered data sources for changes and
    invokes a callback when changes are detected.  A debounce
    interval prevents rapid successive triggers.

    Args:
        config: A :class:`~syncindex.config.SyncIndexConfig` instance.
        interval: Polling interval in seconds (overrides config).
        debounce: Debounce interval in seconds (overrides config).
    """

    def __init__(self, config, interval=None, debounce=None):
        """Initialize the watcher.

        Args:
            config: Application configuration.
            interval: Polling interval in seconds.
            debounce: Debounce interval in seconds.
        """
        self.config = config
        self.interval = interval or config.watch_interval
        self.debounce = debounce or config.watch_debounce
        self.indexer = Indexer(config)
        self._running = False
        self._stop_event = threading.Event()
        self._last_sync_time = 0.0
        self._event_callback = None
        self._sync_count = 0

    def set_event_callback(self, callback):
        """Set a callback invoked when file system changes are detected.

        Args:
            callback: A callable ``callback(events)`` where *events*
                is a list of :class:`WatchEvent`.
        """
        self._event_callback = callback

    def _detect_changes(self):
        """Scan sources and detect changes since the last check.

        Returns:
            A list of :class:`WatchEvent` instances.
        """
        events = []
        old_entries = self.indexer.load_index()

        self.indexer.register_sources_from_config()
        self.indexer.build_index()
        diff = self.indexer.diff(old_entries)

        for entry in diff.added:
            events.append(WatchEvent(WatchEvent.CREATED, entry.path, entry.source))

        for entry in diff.modified:
            events.append(WatchEvent(WatchEvent.MODIFIED, entry.path, entry.source))

        for entry in diff.deleted:
            events.append(WatchEvent(WatchEvent.DELETED, entry.path, entry.source))

        return events

    def _run_sync(self):
        """Execute a sync cycle and save the updated index."""
        try:
            engine = SyncEngine(self.config, self.indexer)
            result = engine.sync(dry_run=False)
            self.indexer.save_index()
            self._sync_count += 1
            return result
        except Exception as exc:
            error(f"Watch sync error: {exc}")
            return None

    def watch(self, callback=None):
        """Start the file system watcher (blocking).

        Continuously polls for changes and triggers synchronization
        when changes are detected.  Blocks until interrupted with
        Ctrl-C (SIGINT) or :meth:`stop` is called.

        Args:
            callback: Optional callback ``callback(events, result)``
                invoked after each sync cycle.
        """
        self._running = True
        self._stop_event.clear()

        info(colored("Watch mode started", Colors.BOLD + Colors.CYAN))
        info(f"  Polling interval: {self.interval}s")
        info(f"  Debounce:         {self.debounce}s")
        info(f"  Press Ctrl+C to stop.\n")

        # Initial sync
        info("Performing initial sync...")
        result = self._run_sync()
        if callback and result:
            callback([], result)

        cycle = 0
        try:
            while self._running and not self._stop_event.is_set():
                cycle += 1
                self._stop_event.wait(self.interval)

                if not self._running or self._stop_event.is_set():
                    break

                # Debounce check
                now = time.time()
                if now - self._last_sync_time < self.debounce:
                    continue

                # Detect changes
                events = self._detect_changes()

                if events:
                    info(colored(
                        f"[Cycle {cycle}] {len(events)} change(s) detected",
                        Colors.YELLOW,
                    ))
                    for event in events:
                        info(f"  {event.event_type}: {event.path}")

                    # Trigger sync
                    result = self._run_sync()
                    self._last_sync_time = time.time()

                    if callback and result:
                        callback(events, result)
                else:
                    # Quiet indicator
                    sys.stdout.write(
                        f"\r  [Cycle {cycle}] No changes... "
                        f"(synced {self._sync_count} time(s))"
                    )
                    sys.stdout.flush()

        except KeyboardInterrupt:
            print()
            info(colored("Watch mode stopped by user.", Colors.YELLOW))

        self._running = False
        info(f"Total sync cycles triggered: {self._sync_count}")

    def watch_async(self, callback=None):
        """Start the watcher in a background thread.

        Args:
            callback: Optional callback for sync events.

        Returns:
            The :class:`threading.Thread` running the watcher.
        """
        thread = threading.Thread(
            target=self.watch,
            args=(callback,),
            daemon=True,
        )
        thread.start()
        return thread

    def stop(self):
        """Signal the watcher to stop.

        The watcher will finish its current cycle and exit.
        """
        self._running = False
        self._stop_event.set()

    @property
    def is_running(self):
        """Whether the watcher is currently active.

        Returns:
            ``True`` if the watcher loop is running.
        """
        return self._running
