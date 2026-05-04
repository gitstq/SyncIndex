"""
Synchronization engine for SyncIndex.

Implements the core incremental sync logic, including change detection,
conflict resolution, and progress tracking.
"""

import os
import shutil
import time

from .indexer import Indexer, IndexEntry, IndexDiff, ChangeType
from .sources import SourceBase
from .utils import (
    colored,
    Colors,
    format_size,
    format_duration,
    info,
    success,
    warning,
    error,
    ensure_directory,
)


class SyncResult:
    """Result of a synchronization operation.

    Attributes:
        start_time: Timestamp when the sync started.
        end_time: Timestamp when the sync finished.
        duration: Elapsed time in seconds.
        diff: The :class:`IndexDiff` for this sync.
        errors: List of error message strings encountered during sync.
        skipped: List of items skipped due to conflicts.
        synced_added: List of successfully added items.
        synced_modified: List of successfully modified items.
        synced_deleted: List of successfully deleted items.
        dry_run: Whether this was a dry-run (no actual changes made).
    """

    def __init__(self, dry_run=False):
        """Initialize a sync result.

        Args:
            dry_run: ``True`` if this was a dry-run sync.
        """
        self.start_time = time.time()
        self.end_time = None
        self.duration = 0.0
        self.diff = None
        self.errors = []
        self.skipped = []
        self.synced_added = []
        self.synced_modified = []
        self.synced_deleted = []
        self.dry_run = dry_run

    def finish(self):
        """Mark the sync as complete and compute duration."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time

    @property
    def success(self):
        """Whether the sync completed without errors.

        Returns:
            ``True`` if no errors were recorded.
        """
        return len(self.errors) == 0

    @property
    def total_synced(self):
        """Total number of items that were synced.

        Returns:
            Sum of added, modified, and deleted synced items.
        """
        return (len(self.synced_added) + len(self.synced_modified)
                + len(self.synced_deleted))

    def summary(self):
        """Generate a human-readable summary of the sync result.

        Returns:
            A formatted multi-line string.
        """
        lines = []
        mode = colored("DRY-RUN", Colors.YELLOW) if self.dry_run else colored("SYNC", Colors.GREEN)
        lines.append(f"\n  {mode} Summary")
        lines.append(f"  {'-' * 40}")
        lines.append(f"  Duration:    {format_duration(self.duration)}")
        lines.append(f"  Added:       {len(self.synced_added)}")
        lines.append(f"  Modified:    {len(self.synced_modified)}")
        lines.append(f"  Deleted:     {len(self.synced_deleted)}")
        lines.append(f"  Skipped:     {len(self.skipped)}")
        lines.append(f"  Errors:      {len(self.errors)}")
        if self.diff:
            lines.append(f"  Total changes detected: {self.diff.total_changes}")
        status = colored("SUCCESS", Colors.GREEN) if self.success else colored("FAILED", Colors.RED)
        lines.append(f"  Status:      {status}")
        lines.append("")
        return "\n".join(lines)

    def to_dict(self):
        """Serialize the sync result to a dictionary.

        Returns:
            Dictionary suitable for JSON serialization.
        """
        return {
            "dry_run": self.dry_run,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "success": self.success,
            "total_synced": self.total_synced,
            "synced_added": len(self.synced_added),
            "synced_modified": len(self.synced_modified),
            "synced_deleted": len(self.synced_deleted),
            "skipped": len(self.skipped),
            "errors": self.errors,
            "diff": self.diff.to_dict() if self.diff else None,
        }


class SyncEngine:
    """Core synchronization engine.

    Coordinates data sources, the indexer, and conflict resolution
    to perform incremental synchronization.

    Args:
        config: A :class:`~syncindex.config.SyncIndexConfig` instance.
        indexer: An optional :class:`Indexer` instance.  If ``None``,
            a new one is created from *config*.
    """

    def __init__(self, config, indexer=None):
        """Initialize the sync engine.

        Args:
            config: Application configuration.
            indexer: Optional pre-configured indexer.
        """
        self.config = config
        self.indexer = indexer or Indexer(config)
        self._progress_callback = None

    def set_progress_callback(self, callback):
        """Set a callback to receive progress updates during sync.

        Args:
            callback: A callable ``callback(message, progress)`` where
                *message* is a string and *progress* is a float in [0, 1].
        """
        self._progress_callback = callback

    def _report_progress(self, message, progress=0.0):
        """Invoke the progress callback if set.

        Args:
            message: Status message.
            progress: Progress value between 0.0 and 1.0.
        """
        if self._progress_callback:
            self._progress_callback(message, progress)

    def sync(self, dry_run=False, target_dir=None):
        """Execute an incremental synchronization.

        The process is:

        1. Register data sources from configuration.
        2. Build a fresh index of the current state.
        3. Compare against the previously saved index.
        4. Apply changes (add / modify / delete) according to the
           configured conflict strategy.
        5. Save the updated index.

        Args:
            dry_run: If ``True``, detect and report changes but do not
                modify any files.
            target_dir: Optional override for the output directory.
                If ``None``, the first source's path is used as reference.

        Returns:
            A :class:`SyncResult` instance.
        """
        result = SyncResult(dry_run=dry_run)

        try:
            # Step 1: Register sources
            self._report_progress("Registering data sources...", 0.0)
            self.indexer.register_sources_from_config()

            if not self.indexer._sources:
                warning("No data sources configured. Nothing to sync.")
                result.finish()
                return result

            # Step 2: Load previous index
            self._report_progress("Loading previous index...", 0.1)
            old_entries = self.indexer.load_index()
            info(f"Previous index: {len(old_entries)} entries")

            # Step 3: Build new index
            self._report_progress("Building new index...", 0.2)

            def on_index_progress(entry, progress):
                self._report_progress(
                    f"Indexing: {entry.path}",
                    0.2 + progress * 0.4,
                )

            self.indexer.build_index(callback=on_index_progress)
            info(f"Current index: {len(self.indexer.entries)} entries")

            # Step 4: Detect changes
            self._report_progress("Detecting changes...", 0.65)
            diff = self.indexer.diff(old_entries)
            result.diff = diff

            if not diff.has_changes:
                info("No changes detected. Index is up to date.")
                if not dry_run:
                    self.indexer.save_index()
                result.finish()
                return result

            info(f"Changes detected: {diff.summary}")

            # Step 5: Apply changes
            self._report_progress("Applying changes...", 0.7)

            if dry_run:
                info(colored("DRY-RUN: No files will be modified.", Colors.YELLOW))
                result.synced_added = list(diff.added)
                result.synced_modified = list(diff.modified)
                result.synced_deleted = list(diff.deleted)
            else:
                self._apply_changes(diff, target_dir, result)

            # Step 6: Save updated index
            if not dry_run:
                self._report_progress("Saving index...", 0.95)
                self.indexer.save_index()
                info("Index saved successfully.")

            self._report_progress("Sync complete.", 1.0)

        except Exception as exc:
            error(f"Sync failed: {exc}")
            result.errors.append(str(exc))

        result.finish()
        return result

    def _apply_changes(self, diff, target_dir, result):
        """Apply detected changes to the target directory.

        Args:
            diff: The :class:`IndexDiff` containing changes.
            target_dir: Target directory path (or ``None``).
            result: The :class:`SyncResult` to update.
        """
        strategy = self.config.conflict_strategy
        delete_orphans = self.config.delete_orphans

        # Process additions
        for entry in diff.added:
            try:
                self._sync_entry(entry, "add", target_dir, strategy, result)
            except Exception as exc:
                result.errors.append(f"Error adding {entry.path}: {exc}")

        # Process modifications
        for entry in diff.modified:
            try:
                self._sync_entry(entry, "modify", target_dir, strategy, result)
            except Exception as exc:
                result.errors.append(f"Error modifying {entry.path}: {exc}")

        # Process deletions
        if delete_orphans:
            for entry in diff.deleted:
                try:
                    self._sync_entry(entry, "delete", target_dir, strategy, result)
                except Exception as exc:
                    result.errors.append(f"Error deleting {entry.path}: {exc}")
        else:
            if diff.deleted:
                info(f"Skipping {len(diff.deleted)} deletions (delete_orphans=False)")

    def _sync_entry(self, entry, action, target_dir, strategy, result):
        """Synchronize a single entry.

        For filesystem sources, this copies files to the target directory.
        For other source types, the entry is recorded but no file I/O
        is performed.

        Args:
            entry: The :class:`IndexEntry` to sync.
            action: One of ``"add"``, ``"modify"``, ``"delete"``.
            target_dir: Target directory path.
            strategy: Conflict resolution strategy.
            result: The :class:`SyncResult` to update.
        """
        if action == "delete":
            if target_dir:
                target_path = os.path.join(target_dir, entry.path)
                if os.path.exists(target_path):
                    os.remove(target_path)
                    result.synced_deleted.append(entry)
                    info(f"  Deleted: {entry.path}")
            else:
                result.synced_deleted.append(entry)
            return

        # Find the source to get the absolute path
        source = None
        for src in self.indexer._sources:
            if src.name == entry.source:
                source = src
                break

        if source is None:
            result.skipped.append(entry)
            warning(f"  Skipped {entry.path}: source '{entry.source}' not found")
            return

        # Get the absolute path of the source file
        src_path = None
        for item in source.enumerate_items(
            include_patterns=self.config.include_patterns,
            exclude_patterns=self.config.exclude_patterns,
        ):
            if item["path"] == entry.path:
                src_path = item.get("absolute_path", item.get("path"))
                break

        if src_path is None or not os.path.isfile(src_path):
            result.skipped.append(entry)
            warning(f"  Skipped {entry.path}: source file not found")
            return

        if target_dir:
            target_path = os.path.join(target_dir, entry.path)

            # Check for conflicts
            if os.path.exists(target_path) and action == "add":
                if strategy == "skip":
                    result.skipped.append(entry)
                    warning(f"  Skipped {entry.path}: conflict (file exists)")
                    return
                elif strategy == "newer_wins":
                    target_mtime = os.path.getmtime(target_path)
                    if target_mtime > entry.mtime:
                        result.skipped.append(entry)
                        warning(f"  Skipped {entry.path}: target is newer")
                        return

            ensure_directory(target_path)
            shutil.copy2(src_path, target_path)

        if action == "add":
            result.synced_added.append(entry)
            info(f"  Added: {entry.path} ({format_size(entry.size)})")
        elif action == "modify":
            result.synced_modified.append(entry)
            info(f"  Modified: {entry.path} ({format_size(entry.size)})")
