"""
Data source adapters for SyncIndex.

Provides a base class and concrete implementations for different
data source types.  Each adapter is responsible for enumerating items
and computing metadata (size, modification time, hash).
"""

import csv
import hashlib
import io
import json
import os

from .utils import compute_file_hash, is_path_excluded


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class SourceBase:
    """Abstract base class for data source adapters.

    Subclasses must implement :meth:`enumerate_items` and should
    override :meth:`get_item_hash` if the default file-based hashing
    is not appropriate.

    Attributes:
        name: Human-readable name of this source.
        source_config: The source configuration dictionary.
    """

    def __init__(self, name, source_config):
        """Initialize the source adapter.

        Args:
            name: A descriptive name for this data source.
            source_config: Dictionary containing source-specific settings.
        """
        self.name = name
        self.source_config = source_config

    def enumerate_items(self, include_patterns=None, exclude_patterns=None):
        """Enumerate all items in this data source.

        Each item is represented as a dictionary with at least the
        following keys:

        - ``path`` -- unique identifier / path within the source
        - ``size`` -- size in bytes (integer)
        - ``mtime`` -- modification time as a Unix timestamp (float)
        - ``type`` -- ``"file"`` or ``"directory"``

        Args:
            include_patterns: Optional glob patterns to include.
            exclude_patterns: Optional glob patterns to exclude.

        Yields:
            Dictionaries describing each item.
        """
        raise NotImplementedError

    def get_item_hash(self, item, algorithm="sha256"):
        """Compute the hash of a data source item.

        The default implementation reads the file at ``item["path"]``
        and hashes its contents.  Subclasses (e.g. :class:`JsonSource`)
        may override this to hash in-memory data.

        Args:
            item: An item dictionary as returned by :meth:`enumerate_items`.
            algorithm: Hash algorithm (``md5``, ``sha1``, ``sha256``).

        Returns:
            Hexadecimal hash string.
        """
        filepath = item.get("absolute_path", item.get("path", ""))
        if os.path.isfile(filepath):
            return compute_file_hash(filepath, algorithm)
        return hashlib.new(algorithm, item["path"].encode("utf-8")).hexdigest()

    def get_item_content(self, item):
        """Read the content of an item as bytes.

        Args:
            item: An item dictionary.

        Returns:
            Bytes content of the item.
        """
        filepath = item.get("absolute_path", item.get("path", ""))
        if os.path.isfile(filepath):
            with open(filepath, "rb") as fh:
                return fh.read()
        return b""

    def __repr__(self):
        return f"<{self.__class__.__name__} name='{self.name}'>"


# ---------------------------------------------------------------------------
# Filesystem source
# ---------------------------------------------------------------------------

class FileSystemSource(SourceBase):
    """Data source backed by the local file system.

    Supports both single files and recursive directory scanning.

    Configuration keys:
        - ``path`` (required): Root path to scan.
        - ``recursive`` (optional): Whether to recurse into subdirectories
          (default ``True``).
    """

    def __init__(self, name, source_config):
        """Initialize the filesystem source.

        Args:
            name: Descriptive name.
            source_config: Must contain a ``"path"`` key.
        """
        super().__init__(name, source_config)
        self.root_path = os.path.abspath(source_config.get("path", "."))
        self.recursive = source_config.get("recursive", True)

    def enumerate_items(self, include_patterns=None, exclude_patterns=None):
        """Walk the filesystem and yield item dictionaries.

        Args:
            include_patterns: Glob patterns for inclusion.
            exclude_patterns: Glob patterns for exclusion.

        Yields:
            Item dictionaries for each file found.
        """
        if not os.path.exists(self.root_path):
            return

        if os.path.isfile(self.root_path):
            stat = os.stat(self.root_path)
            rel_path = os.path.basename(self.root_path)
            yield {
                "path": rel_path,
                "absolute_path": self.root_path,
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "type": "file",
                "source": self.name,
            }
            return

        if self.recursive:
            yield from self._walk_directory(self.root_path, include_patterns, exclude_patterns)
        else:
            yield from self._list_directory(self.root_path, include_patterns, exclude_patterns)

    def _walk_directory(self, directory, include_patterns, exclude_patterns):
        """Recursively walk a directory tree.

        Args:
            directory: The directory to walk.
            include_patterns: Glob patterns for inclusion.
            exclude_patterns: Glob patterns for exclusion.

        Yields:
            Item dictionaries.
        """
        for dirpath, dirnames, filenames in os.walk(directory):
            # Filter out excluded directories in-place to prevent os.walk
            # from descending into them.
            dirnames[:] = [
                d for d in dirnames
                if not is_path_excluded(d, include_patterns, exclude_patterns)
            ]

            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(full_path, self.root_path)

                if is_path_excluded(rel_path, include_patterns, exclude_patterns):
                    continue

                try:
                    stat = os.stat(full_path)
                except OSError:
                    continue

                yield {
                    "path": rel_path,
                    "absolute_path": full_path,
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                    "type": "file",
                    "source": self.name,
                }

    def _list_directory(self, directory, include_patterns, exclude_patterns):
        """List files in a single directory (non-recursive).

        Args:
            directory: The directory to list.
            include_patterns: Glob patterns for inclusion.
            exclude_patterns: Glob patterns for exclusion.

        Yields:
            Item dictionaries.
        """
        try:
            entries = os.listdir(directory)
        except OSError:
            return

        for entry in entries:
            full_path = os.path.join(directory, entry)
            if not os.path.isfile(full_path):
                continue

            if is_path_excluded(entry, include_patterns, exclude_patterns):
                continue

            try:
                stat = os.stat(full_path)
            except OSError:
                continue

            yield {
                "path": entry,
                "absolute_path": full_path,
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "type": "file",
                "source": self.name,
            }


# ---------------------------------------------------------------------------
# JSON source
# ---------------------------------------------------------------------------

class JsonSource(SourceBase):
    """Data source backed by a JSON file.

    Each top-level key in the JSON file is treated as a named record.
    The hash is computed over the serialized value of each record.

    Configuration keys:
        - ``path`` (required): Path to the JSON file.
        - ``key_field`` (optional): Field within each record to use as
          the item path (default: the top-level key).
    """

    def __init__(self, name, source_config):
        """Initialize the JSON source.

        Args:
            name: Descriptive name.
            source_config: Must contain a ``"path"`` key.
        """
        super().__init__(name, source_config)
        self.file_path = os.path.abspath(source_config.get("path", ""))
        self.key_field = source_config.get("key_field", None)
        self._data = None

    def _load_data(self):
        """Lazily load and cache the JSON data.

        Returns:
            The parsed JSON data (dict or list).
        """
        if self._data is None and os.path.isfile(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as fh:
                self._data = json.load(fh)
        return self._data

    def enumerate_items(self, include_patterns=None, exclude_patterns=None):
        """Enumerate records from the JSON file.

        Args:
            include_patterns: Glob patterns for inclusion.
            exclude_patterns: Glob patterns for exclusion.

        Yields:
            Item dictionaries for each JSON record.
        """
        data = self._load_data()
        if data is None:
            return

        if isinstance(data, dict):
            for key, value in data.items():
                if is_path_excluded(str(key), include_patterns, exclude_patterns):
                    continue
                serialized = json.dumps(value, sort_keys=True, ensure_ascii=False)
                yield {
                    "path": str(key),
                    "absolute_path": self.file_path,
                    "size": len(serialized.encode("utf-8")),
                    "mtime": os.path.getmtime(self.file_path),
                    "type": "record",
                    "source": self.name,
                    "_content": serialized.encode("utf-8"),
                }
        elif isinstance(data, list):
            for idx, record in enumerate(data):
                key = str(idx)
                if self.key_field and isinstance(record, dict):
                    key = str(record.get(self.key_field, idx))
                if is_path_excluded(key, include_patterns, exclude_patterns):
                    continue
                serialized = json.dumps(record, sort_keys=True, ensure_ascii=False)
                yield {
                    "path": key,
                    "absolute_path": self.file_path,
                    "size": len(serialized.encode("utf-8")),
                    "mtime": os.path.getmtime(self.file_path),
                    "type": "record",
                    "source": self.name,
                    "_content": serialized.encode("utf-8"),
                }

    def get_item_hash(self, item, algorithm="sha256"):
        """Hash a JSON record using its serialized content.

        Args:
            item: Item dictionary from :meth:`enumerate_items`.
            algorithm: Hash algorithm name.

        Returns:
            Hexadecimal hash string.
        """
        content = item.get("_content", b"")
        if content:
            return hashlib.new(algorithm, content).hexdigest()
        return super().get_item_hash(item, algorithm)

    def get_item_content(self, item):
        """Return the serialized content of a JSON record.

        Args:
            item: Item dictionary.

        Returns:
            Bytes content.
        """
        return item.get("_content", b"")


# ---------------------------------------------------------------------------
# CSV source
# ---------------------------------------------------------------------------

class CsvSource(SourceBase):
    """Data source backed by a CSV file.

    Each row in the CSV is treated as a record.  A ``key_field``
    column can be used to generate unique item identifiers; otherwise
    row indices are used.

    Configuration keys:
        - ``path`` (required): Path to the CSV file.
        - ``key_field`` (optional): Column name to use as the item key.
        - ``delimiter`` (optional): Field delimiter (default ``","``).
        - ``encoding`` (optional): File encoding (default ``"utf-8"``).
    """

    def __init__(self, name, source_config):
        """Initialize the CSV source.

        Args:
            name: Descriptive name.
            source_config: Must contain a ``"path"`` key.
        """
        super().__init__(name, source_config)
        self.file_path = os.path.abspath(source_config.get("path", ""))
        self.key_field = source_config.get("key_field", None)
        self.delimiter = source_config.get("delimiter", ",")
        self.encoding = source_config.get("encoding", "utf-8")
        self._rows = None
        self._fieldnames = None

    def _load_data(self):
        """Lazily load and cache the CSV data.

        Returns:
            Tuple of (fieldnames, rows) where *rows* is a list of dicts.
        """
        if self._rows is None and os.path.isfile(self.file_path):
            with open(self.file_path, "r", encoding=self.encoding, newline="") as fh:
                reader = csv.DictReader(fh, delimiter=self.delimiter)
                self._fieldnames = reader.fieldnames or []
                self._rows = list(reader)
        return self._fieldnames, self._rows

    def enumerate_items(self, include_patterns=None, exclude_patterns=None):
        """Enumerate rows from the CSV file.

        Args:
            include_patterns: Glob patterns for inclusion.
            exclude_patterns: Glob patterns for exclusion.

        Yields:
            Item dictionaries for each CSV row.
        """
        fieldnames, rows = self._load_data()
        if rows is None:
            return

        for idx, row in enumerate(rows):
            key = str(idx)
            if self.key_field and self.key_field in row:
                key = str(row[self.key_field])

            if is_path_excluded(key, include_patterns, exclude_patterns):
                continue

            serialized = json.dumps(row, sort_keys=True, ensure_ascii=False)
            yield {
                "path": key,
                "absolute_path": self.file_path,
                "size": len(serialized.encode("utf-8")),
                "mtime": os.path.getmtime(self.file_path),
                "type": "record",
                "source": self.name,
                "_content": serialized.encode("utf-8"),
                "_row": row,
            }

    def get_item_hash(self, item, algorithm="sha256"):
        """Hash a CSV row using its serialized content.

        Args:
            item: Item dictionary from :meth:`enumerate_items`.
            algorithm: Hash algorithm name.

        Returns:
            Hexadecimal hash string.
        """
        content = item.get("_content", b"")
        if content:
            return hashlib.new(algorithm, content).hexdigest()
        return super().get_item_hash(item, algorithm)

    def get_item_content(self, item):
        """Return the serialized content of a CSV row.

        Args:
            item: Item dictionary.

        Returns:
            Bytes content.
        """
        return item.get("_content", b"")


# ---------------------------------------------------------------------------
# Source factory
# ---------------------------------------------------------------------------

SOURCE_REGISTRY = {
    "filesystem": FileSystemSource,
    "json": JsonSource,
    "csv": CsvSource,
}


def create_source(source_config):
    """Instantiate a data source adapter from its configuration.

    Args:
        source_config: Dictionary with at least ``"name"`` and ``"type"``
            keys.

    Returns:
        A :class:`SourceBase` subclass instance.

    Raises:
        ValueError: If the source type is not recognized.
    """
    source_type = source_config.get("type", "filesystem").lower()
    name = source_config.get("name", "unnamed")

    cls = SOURCE_REGISTRY.get(source_type)
    if cls is None:
        raise ValueError(
            f"Unknown source type '{source_type}'. "
            f"Available types: {', '.join(sorted(SOURCE_REGISTRY))}"
        )

    return cls(name, source_config)
