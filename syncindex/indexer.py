"""
Index engine for SyncIndex.

Builds and maintains a persistent index of data source items, using
file hashes and modification times for incremental change detection.
The index is stored as a JSON file on disk.
"""

import os
import time

from .sources import SourceBase, create_source
from .utils import (
    safe_read_json,
    safe_write_json,
    ensure_directory,
    format_size,
    info,
    warning,
)


class IndexEntry:
    """A single entry in the SyncIndex.

    Represents the indexed state of one item (file, record, etc.).

    Attributes:
        path: Unique identifier within the source.
        source: Name of the data source.
        size: Size in bytes.
        mtime: Last modification time (Unix timestamp).
        hash: Hash digest string.
        item_type: Type of item (``"file"`` or ``"record"``).
        indexed_at: Timestamp when this entry was last indexed.
    """

    def __init__(self, path, source, size=0, mtime=0.0, hash_value="",
                 item_type="file", indexed_at=None):
        """Initialize an index entry.

        Args:
            path: Unique path/identifier.
            source: Data source name.
            size: Size in bytes.
            mtime: Modification timestamp.
            hash_value: Hash digest string.
            item_type: ``"file"`` or ``"record"``.
            indexed_at: When this entry was created/updated.
        """
        self.path = path
        self.source = source
        self.size = size
        self.mtime = mtime
        self.hash = hash_value
        self.item_type = item_type
        self.indexed_at = indexed_at or time.time()

    def to_dict(self):
        """Serialize the entry to a plain dictionary.

        Returns:
            Dictionary suitable for JSON serialization.
        """
        return {
            "path": self.path,
            "source": self.source,
            "size": self.size,
            "mtime": self.mtime,
            "hash": self.hash,
            "type": self.item_type,
            "indexed_at": self.indexed_at,
        }

    @classmethod
    def from_dict(cls, data):
        """Create an IndexEntry from a dictionary.

        Args:
            data: Dictionary with entry fields.

        Returns:
            A new :class:`IndexEntry` instance.
        """
        return cls(
            path=data.get("path", ""),
            source=data.get("source", ""),
            size=data.get("size", 0),
            mtime=data.get("mtime", 0.0),
            hash_value=data.get("hash", ""),
            item_type=data.get("type", "file"),
            indexed_at=data.get("indexed_at"),
        )

    def __repr__(self):
        return (
            f"IndexEntry(path='{self.path}', source='{self.source}', "
            f"hash='{self.hash[:12]}...')"
        )

    def __eq__(self, other):
        if not isinstance(other, IndexEntry):
            return NotImplemented
        return (self.path == other.path and self.source == other.source
                and self.hash == other.hash)

    def __hash__(self):
        return hash((self.path, self.source, self.hash))


class ChangeType:
    """Constants representing types of changes detected between indexes."""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    UNCHANGED = "unchanged"


class IndexDiff:
    """Result of comparing two index snapshots.

    Attributes:
        added: List of :class:`IndexEntry` items present in the new index
            but not in the old one.
        modified: List of :class:`IndexEntry` items whose hash or mtime
            differs between the two indexes.
        deleted: List of :class:`IndexEntry` items present in the old index
            but absent from the new one.
        unchanged: List of :class:`IndexEntry` items that are identical
            in both indexes.
    """

    def __init__(self):
        """Initialize an empty diff."""
        self.added = []
        self.modified = []
        self.deleted = []
        self.unchanged = []

    @property
    def has_changes(self):
        """Whether any changes were detected.

        Returns:
            ``True`` if there are added, modified, or deleted entries.
        """
        return bool(self.added or self.modified or self.deleted)

    @property
    def total_changes(self):
        """Total number of changed entries.

        Returns:
            Sum of added, modified, and deleted counts.
        """
        return len(self.added) + len(self.modified) + len(self.deleted)

    @property
    def summary(self):
        """Human-readable summary of the diff.

        Returns:
            A formatted string summarizing the changes.
        """
        parts = []
        if self.added:
            parts.append(f"{len(self.added)} added")
        if self.modified:
            parts.append(f"{len(self.modified)} modified")
        if self.deleted:
            parts.append(f"{len(self.deleted)} deleted")
        if self.unchanged:
            parts.append(f"{len(self.unchanged)} unchanged")
        return ", ".join(parts) if parts else "no changes"

    def to_dict(self):
        """Serialize the diff to a dictionary.

        Returns:
            Dictionary with change lists.
        """
        return {
            "added": [e.to_dict() for e in self.added],
            "modified": [e.to_dict() for e in self.modified],
            "deleted": [e.to_dict() for e in self.deleted],
            "unchanged": [e.to_dict() for e in self.unchanged],
            "total_changes": self.total_changes,
        }


class Indexer:
    """Builds and manages the persistent item index.

    The indexer scans data sources, computes hashes, and stores the
    resulting index to disk.  On subsequent runs it can detect changes
    by comparing the current state against the stored index.

    Args:
        config: A :class:`~syncindex.config.SyncIndexConfig` instance.
    """

    def __init__(self, config):
        """Initialize the indexer.

        Args:
            config: Application configuration object.
        """
        self.config = config
        self.storage_path = os.path.abspath(config.storage_path)
        self._entries = {}  # key: (source, path) -> IndexEntry
        self._sources = []

    @property
    def entries(self):
        """Dictionary of current index entries.

        Returns:
            Dict mapping ``(source_name, path)`` to :class:`IndexEntry`.
        """
        return self._entries

    def register_source(self, source):
        """Register a data source for indexing.

        Args:
            source: A :class:`~syncindex.sources.SourceBase` instance.
        """
        if not isinstance(source, SourceBase):
            raise TypeError(f"Expected SourceBase, got {type(source).__name__}")
        self._sources.append(source)

    def register_sources_from_config(self):
        """Create and register sources from the configuration.

        Iterates over :pyattr:`config.sources` and instantiates the
        appropriate adapter for each.
        """
        for source_config in self.config.sources:
            source = create_source(source_config)
            self.register_source(source)
            info(f"Registered source: {source.name} ({source_config.get('type', 'filesystem')})")

    def build_index(self, callback=None):
        """Scan all registered sources and build a fresh index.

        Args:
            callback: Optional callable ``callback(entry, progress)``
                invoked for each indexed entry.  *progress* is a float
                between 0.0 and 1.0.

        Returns:
            A list of :class:`IndexEntry` for all indexed items.
        """
        self._entries.clear()
        all_items = []

        # Collect all items from all sources
        for source in self._sources:
            items = list(source.enumerate_items(
                include_patterns=self.config.include_patterns,
                exclude_patterns=self.config.exclude_patterns,
            ))
            all_items.extend(items)

        total = len(all_items)
        algorithm = self.config.hash_algorithm

        # Build a lookup from source name to source object
        source_map = {s.name: s for s in self._sources}

        for idx, item in enumerate(all_items):
            item_source = item.get("source", "unknown")
            src_obj = source_map.get(item_source)

            hash_value = ""
            if src_obj:
                hash_value = src_obj.get_item_hash(item, algorithm)

            entry = IndexEntry(
                path=item["path"],
                source=item_source,
                size=item.get("size", 0),
                mtime=item.get("mtime", 0.0),
                hash_value=hash_value,
                item_type=item.get("type", "file"),
            )

            key = (entry.source, entry.path)
            self._entries[key] = entry

            if callback:
                progress = (idx + 1) / total if total > 0 else 1.0
                callback(entry, progress)

        return list(self._entries.values())

    def load_index(self):
        """Load a previously saved index from disk.

        Returns:
            A dictionary mapping ``(source, path)`` to
            :class:`IndexEntry`, or an empty dict if no index exists.
        """
        data = safe_read_json(self.storage_path, default=None)
        if data is None:
            return {}

        entries = {}
        index_data = data.get("entries", data) if isinstance(data, dict) else data

        if isinstance(index_data, dict):
            # Format: {"entries": [...]}
            for entry_data in index_data.get("entries", []):
                entry = IndexEntry.from_dict(entry_data)
                entries[(entry.source, entry.path)] = entry
        elif isinstance(index_data, list):
            # Format: [...]
            for entry_data in index_data:
                entry = IndexEntry.from_dict(entry_data)
                entries[(entry.source, entry.path)] = entry

        return entries

    def save_index(self):
        """Persist the current index to disk.

        The index is written atomically to avoid corruption.
        """
        data = {
            "version": self.config.version,
            "hash_algorithm": self.config.hash_algorithm,
            "indexed_at": time.time(),
            "total_entries": len(self._entries),
            "entries": [e.to_dict() for e in self._entries.values()],
        }
        ensure_directory(self.storage_path)
        safe_write_json(self.storage_path, data)

    def diff(self, old_entries=None):
        """Compare the current in-memory index against a previous snapshot.

        If *old_entries* is ``None``, the index is loaded from disk
        automatically.

        Change detection uses a dual-check strategy:

        1. **Hash comparison** -- if the hash differs, the item is
           marked as modified.
        2. **Modification time** -- if the mtime differs but the hash
           is the same, the item is considered unchanged (handles
           cases where mtime changes without content changes).

        Args:
            old_entries: Optional dict of ``(source, path)`` ->
                :class:`IndexEntry`.  If ``None``, loaded from disk.

        Returns:
            An :class:`IndexDiff` instance.
        """
        if old_entries is None:
            old_entries = self.load_index()

        result = IndexDiff()
        current_keys = set(self._entries.keys())
        old_keys = set(old_entries.keys())

        # Added entries
        for key in current_keys - old_keys:
            result.added.append(self._entries[key])

        # Deleted entries
        for key in old_keys - current_keys:
            result.deleted.append(old_entries[key])

        # Check for modifications
        for key in current_keys & old_keys:
            current = self._entries[key]
            old = old_entries[key]

            if current.hash != old.hash:
                result.modified.append(current)
            else:
                result.unchanged.append(current)

        return result

    def get_status(self):
        """Get a summary of the current index state.

        Returns:
            A dictionary with index statistics.
        """
        entries = self.load_index()
        total_size = sum(e.size for e in entries.values())
        sources = {}
        for entry in entries.values():
            sources[entry.source] = sources.get(entry.source, 0) + 1

        return {
            "total_entries": len(entries),
            "total_size": total_size,
            "total_size_formatted": format_size(total_size),
            "sources": sources,
            "storage_path": self.storage_path,
            "hash_algorithm": self.config.hash_algorithm,
            "index_exists": os.path.isfile(self.storage_path),
        }
