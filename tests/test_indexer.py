"""
Unit tests for the SyncIndex indexer module.

Tests cover index building, change detection, persistence, and
utility functions.  Uses only the Python standard library (unittest).
"""

import hashlib
import json
import os
import shutil
import tempfile
import time
import unittest

# Add the parent directory to sys.path so we can import the package
# when running tests directly (python -m pytest or python -m unittest).
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from syncindex.indexer import IndexEntry, IndexDiff, ChangeType, Indexer
from syncindex.config import SyncIndexConfig, DEFAULT_CONFIG
from syncindex.sources import FileSystemSource, JsonSource, CsvSource
from syncindex.utils import (
    compute_file_hash,
    compute_bytes_hash,
    match_patterns,
    is_path_excluded,
    format_size,
    format_duration,
    format_timestamp,
    safe_read_json,
    safe_write_json,
)


class TestComputeFileHash(unittest.TestCase):
    """Tests for file hash computation."""

    def setUp(self):
        """Create a temporary file for hashing tests."""
        self.tmpdir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.tmpdir, "test.txt")
        with open(self.test_file, "w") as f:
            f.write("hello world")

    def tearDown(self):
        """Clean up temporary files."""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_md5_hash(self):
        """MD5 hash should match the expected value."""
        result = compute_file_hash(self.test_file, "md5")
        expected = hashlib.md5(b"hello world").hexdigest()
        self.assertEqual(result, expected)

    def test_sha1_hash(self):
        """SHA1 hash should match the expected value."""
        result = compute_file_hash(self.test_file, "sha1")
        expected = hashlib.sha1(b"hello world").hexdigest()
        self.assertEqual(result, expected)

    def test_sha256_hash(self):
        """SHA256 hash should match the expected value."""
        result = compute_file_hash(self.test_file, "sha256")
        expected = hashlib.sha256(b"hello world").hexdigest()
        self.assertEqual(result, expected)

    def test_unsupported_algorithm(self):
        """Unsupported algorithm should raise ValueError."""
        with self.assertRaises(ValueError):
            compute_file_hash(self.test_file, "blake2")

    def test_nonexistent_file(self):
        """Non-existent file should raise FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            compute_file_hash("/nonexistent/file.txt", "sha256")


class TestComputeBytesHash(unittest.TestCase):
    """Tests for bytes hash computation."""

    def test_sha256_bytes(self):
        """Hash of known bytes should match expected value."""
        result = compute_bytes_hash(b"test data", "sha256")
        expected = hashlib.sha256(b"test data").hexdigest()
        self.assertEqual(result, expected)


class TestMatchPatterns(unittest.TestCase):
    """Tests for glob pattern matching."""

    def test_match_extension(self):
        """Should match files by extension."""
        self.assertTrue(match_patterns("file.pyc", ["*.pyc"]))
        self.assertFalse(match_patterns("file.py", ["*.pyc"]))

    def test_match_name(self):
        """Should match files by exact name."""
        self.assertTrue(match_patterns("__pycache__", ["__pycache__"]))

    def test_match_multiple_patterns(self):
        """Should match if any pattern hits."""
        patterns = ["*.pyc", "__pycache__", ".DS_Store"]
        self.assertTrue(match_patterns("file.pyc", patterns))
        self.assertTrue(match_patterns("__pycache__", patterns))
        self.assertTrue(match_patterns(".DS_Store", patterns))
        self.assertFalse(match_patterns("normal.txt", patterns))

    def test_empty_patterns(self):
        """Empty pattern list should not match anything."""
        self.assertFalse(match_patterns("anything.txt", []))

    def test_none_patterns(self):
        """None patterns should not match anything."""
        self.assertFalse(match_patterns("anything.txt", None))


class TestIsPathExcluded(unittest.TestCase):
    """Tests for include/exclude path filtering."""

    def test_exclude_only(self):
        """Should exclude matching patterns."""
        self.assertTrue(is_path_excluded(
            "file.pyc", exclude_patterns=["*.pyc"]
        ))
        self.assertFalse(is_path_excluded(
            "file.py", exclude_patterns=["*.pyc"]
        ))

    def test_include_only(self):
        """Should exclude non-matching include patterns."""
        self.assertFalse(is_path_excluded(
            "file.py", include_patterns=["*.py"]
        ))
        self.assertTrue(is_path_excluded(
            "file.txt", include_patterns=["*.py"]
        ))

    def test_include_and_exclude(self):
        """Exclude should take priority over include."""
        self.assertTrue(is_path_excluded(
            "file.py", include_patterns=["*.py"], exclude_patterns=["file.py"]
        ))

    def test_no_patterns(self):
        """No patterns means nothing is excluded."""
        self.assertFalse(is_path_excluded("anything.txt"))


class TestFormatSize(unittest.TestCase):
    """Tests for human-readable size formatting."""

    def test_bytes(self):
        self.assertEqual(format_size(0), "0 B")
        self.assertEqual(format_size(100), "100 B")

    def test_kilobytes(self):
        result = format_size(1024)
        self.assertIn("KB", result)

    def test_megabytes(self):
        result = format_size(1024 * 1024)
        self.assertIn("MB", result)

    def test_gigabytes(self):
        result = format_size(1024 * 1024 * 1024)
        self.assertIn("GB", result)

    def test_negative(self):
        self.assertEqual(format_size(-1), "0 B")


class TestFormatDuration(unittest.TestCase):
    """Tests for duration formatting."""

    def test_subsecond(self):
        result = format_duration(0.45)
        self.assertTrue(result.endswith("s"))
        self.assertIn("0.", result)

    def test_seconds(self):
        result = format_duration(5.0)
        self.assertTrue(result.endswith("s"))

    def test_minutes(self):
        result = format_duration(65.0)
        self.assertIn("m", result)
        self.assertIn("s", result)


class TestIndexEntry(unittest.TestCase):
    """Tests for IndexEntry creation and serialization."""

    def test_create_entry(self):
        """IndexEntry should store all fields correctly."""
        entry = IndexEntry(
            path="test.txt",
            source="local",
            size=1024,
            mtime=1234567890.0,
            hash_value="abc123",
            item_type="file",
        )
        self.assertEqual(entry.path, "test.txt")
        self.assertEqual(entry.source, "local")
        self.assertEqual(entry.size, 1024)
        self.assertEqual(entry.hash, "abc123")

    def test_to_dict(self):
        """to_dict should produce a serializable dictionary."""
        entry = IndexEntry("a.txt", "src", 100, 0.0, "hash1")
        d = entry.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["path"], "a.txt")
        self.assertEqual(d["hash"], "hash1")

    def test_from_dict(self):
        """from_dict should reconstruct an IndexEntry."""
        data = {
            "path": "b.txt",
            "source": "src2",
            "size": 200,
            "mtime": 1.0,
            "hash": "hash2",
            "type": "file",
        }
        entry = IndexEntry.from_dict(data)
        self.assertEqual(entry.path, "b.txt")
        self.assertEqual(entry.hash, "hash2")

    def test_equality(self):
        """Entries with same path, source, and hash should be equal."""
        e1 = IndexEntry("a.txt", "src", 100, 0.0, "h1")
        e2 = IndexEntry("a.txt", "src", 100, 0.0, "h1")
        self.assertEqual(e1, e2)

    def test_inequality(self):
        """Entries with different hashes should not be equal."""
        e1 = IndexEntry("a.txt", "src", 100, 0.0, "h1")
        e2 = IndexEntry("a.txt", "src", 100, 0.0, "h2")
        self.assertNotEqual(e1, e2)


class TestIndexDiff(unittest.TestCase):
    """Tests for index difference computation."""

    def test_empty_diff(self):
        """Empty diff should report no changes."""
        diff = IndexDiff()
        self.assertFalse(diff.has_changes)
        self.assertEqual(diff.total_changes, 0)

    def test_has_changes(self):
        """Diff with added items should report changes."""
        diff = IndexDiff()
        diff.added.append(IndexEntry("a.txt", "src", 0, 0.0, "h"))
        self.assertTrue(diff.has_changes)
        self.assertEqual(diff.total_changes, 1)

    def test_summary(self):
        """Summary should describe all change types."""
        diff = IndexDiff()
        diff.added.append(IndexEntry("a", "s", 0, 0.0, "h"))
        diff.modified.append(IndexEntry("b", "s", 0, 0.0, "h"))
        diff.deleted.append(IndexEntry("c", "s", 0, 0.0, "h"))
        diff.unchanged.append(IndexEntry("d", "s", 0, 0.0, "h"))
        summary = diff.summary
        self.assertIn("1 added", summary)
        self.assertIn("1 modified", summary)
        self.assertIn("1 deleted", summary)
        self.assertIn("1 unchanged", summary)

    def test_to_dict(self):
        """to_dict should produce a valid dictionary."""
        diff = IndexDiff()
        diff.added.append(IndexEntry("a", "s", 0, 0.0, "h"))
        d = diff.to_dict()
        self.assertEqual(d["total_changes"], 1)
        self.assertEqual(len(d["added"]), 1)


class TestIndexer(unittest.TestCase):
    """Tests for the Indexer class."""

    def setUp(self):
        """Create a temporary directory with test files."""
        self.tmpdir = tempfile.mkdtemp()
        self.storage_dir = os.path.join(self.tmpdir, ".syncindex")
        os.makedirs(self.storage_dir)
        self.storage_path = os.path.join(self.storage_dir, "index.json")

        # Create test files
        self.file_a = os.path.join(self.tmpdir, "a.txt")
        self.file_b = os.path.join(self.tmpdir, "b.txt")
        with open(self.file_a, "w") as f:
            f.write("content A")
        with open(self.file_b, "w") as f:
            f.write("content B")

        # Create config
        config_data = dict(DEFAULT_CONFIG)
        config_data["index"]["storage_path"] = self.storage_path
        config_data["sources"] = [
            {
                "name": "test_source",
                "type": "filesystem",
                "path": self.tmpdir,
                "recursive": False,
            }
        ]
        self.config = SyncIndexConfig(config_data)
        self.indexer = Indexer(self.config)

    def tearDown(self):
        """Clean up temporary files."""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_register_source(self):
        """Should register a filesystem source."""
        source = FileSystemSource("test", {"path": self.tmpdir})
        self.indexer.register_source(source)
        self.assertEqual(len(self.indexer._sources), 1)

    def test_register_invalid_source(self):
        """Should reject non-SourceBase objects."""
        with self.assertRaises(TypeError):
            self.indexer.register_source("not a source")

    def test_build_index(self):
        """Building index should enumerate all files."""
        self.indexer.register_sources_from_config()
        entries = self.indexer.build_index()
        # Should have at least 2 files (a.txt and b.txt)
        self.assertGreaterEqual(len(entries), 2)

    def test_save_and_load_index(self):
        """Saved index should be loadable and match the original."""
        self.indexer.register_sources_from_config()
        self.indexer.build_index()
        self.indexer.save_index()

        self.assertTrue(os.path.isfile(self.storage_path))

        loaded = self.indexer.load_index()
        self.assertEqual(len(loaded), len(self.indexer.entries))

    def test_diff_no_previous(self):
        """Diff against no previous index should show all as added."""
        self.indexer.register_sources_from_config()
        self.indexer.build_index()
        diff = self.indexer.diff({})
        self.assertGreater(len(diff.added), 0)
        self.assertEqual(len(diff.deleted), 0)

    def test_diff_unchanged(self):
        """Diff against identical index should show no changes."""
        self.indexer.register_sources_from_config()
        self.indexer.build_index()
        self.indexer.save_index()

        # Rebuild the same index
        old_entries = self.indexer.load_index()
        self.indexer._entries.clear()
        self.indexer.build_index()
        diff = self.indexer.diff(old_entries)
        self.assertEqual(len(diff.added), 0)
        self.assertEqual(len(diff.modified), 0)
        self.assertEqual(len(diff.deleted), 0)

    def test_diff_modified(self):
        """Modifying a file should be detected as a change."""
        self.indexer.register_sources_from_config()
        self.indexer.build_index()
        self.indexer.save_index()

        # Modify a file
        time.sleep(0.01)  # Ensure mtime changes
        with open(self.file_a, "w") as f:
            f.write("modified content A")

        old_entries = self.indexer.load_index()
        self.indexer._entries.clear()
        self.indexer.build_index()
        diff = self.indexer.diff(old_entries)
        modified_paths = [e.path for e in diff.modified]
        self.assertIn("a.txt", modified_paths)

    def test_diff_deleted(self):
        """Deleting a file should be detected."""
        self.indexer.register_sources_from_config()
        self.indexer.build_index()
        self.indexer.save_index()

        # Delete a file
        os.remove(self.file_a)

        old_entries = self.indexer.load_index()
        self.indexer._entries.clear()
        self.indexer.build_index()
        diff = self.indexer.diff(old_entries)
        deleted_paths = [e.path for e in diff.deleted]
        self.assertIn("a.txt", deleted_paths)

    def test_get_status(self):
        """Status should report correct statistics."""
        self.indexer.register_sources_from_config()
        self.indexer.build_index()
        self.indexer.save_index()

        status = self.indexer.get_status()
        self.assertTrue(status["index_exists"])
        self.assertGreater(status["total_entries"], 0)
        self.assertIn("test_source", status["sources"])


class TestFileSystemSource(unittest.TestCase):
    """Tests for the FileSystemSource adapter."""

    def setUp(self):
        """Create a temporary directory with test files."""
        self.tmpdir = tempfile.mkdtemp()
        # Create files
        with open(os.path.join(self.tmpdir, "keep.py"), "w") as f:
            f.write("print('hello')")
        with open(os.path.join(self.tmpdir, "ignore.pyc"), "w") as f:
            f.write("compiled")
        # Create subdirectory
        subdir = os.path.join(self.tmpdir, "subdir")
        os.makedirs(subdir)
        with open(os.path.join(subdir, "nested.txt"), "w") as f:
            f.write("nested content")

    def tearDown(self):
        """Clean up temporary files."""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_enumerate_recursive(self):
        """Recursive scan should find files in subdirectories."""
        source = FileSystemSource("test", {"path": self.tmpdir, "recursive": True})
        items = list(source.enumerate_items())
        paths = [item["path"] for item in items]
        self.assertIn("keep.py", paths)
        self.assertIn(os.path.join("subdir", "nested.txt"), paths)

    def test_enumerate_non_recursive(self):
        """Non-recursive scan should not enter subdirectories."""
        source = FileSystemSource("test", {"path": self.tmpdir, "recursive": False})
        items = list(source.enumerate_items())
        paths = [item["path"] for item in items]
        self.assertIn("keep.py", paths)
        # nested.txt should not be found
        self.assertFalse(any("nested.txt" in p for p in paths))

    def test_enumerate_with_exclude(self):
        """Exclude patterns should filter out matching files."""
        source = FileSystemSource("test", {"path": self.tmpdir, "recursive": False})
        items = list(source.enumerate_items(exclude_patterns=["*.pyc"]))
        paths = [item["path"] for item in items]
        self.assertNotIn("ignore.pyc", paths)
        self.assertIn("keep.py", paths)

    def test_enumerate_with_include(self):
        """Include patterns should only return matching files."""
        source = FileSystemSource("test", {"path": self.tmpdir, "recursive": False})
        items = list(source.enumerate_items(include_patterns=["*.py"]))
        paths = [item["path"] for item in items]
        self.assertIn("keep.py", paths)
        self.assertNotIn("ignore.pyc", paths)

    def test_single_file_source(self):
        """Source pointing to a single file should yield one item."""
        filepath = os.path.join(self.tmpdir, "keep.py")
        source = FileSystemSource("test", {"path": filepath})
        items = list(source.enumerate_items())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["path"], "keep.py")

    def test_nonexistent_path(self):
        """Non-existent path should yield no items."""
        source = FileSystemSource("test", {"path": "/nonexistent/path"})
        items = list(source.enumerate_items())
        self.assertEqual(len(items), 0)


class TestJsonSource(unittest.TestCase):
    """Tests for the JsonSource adapter."""

    def setUp(self):
        """Create a temporary JSON file."""
        self.tmpdir = tempfile.mkdtemp()
        self.json_file = os.path.join(self.tmpdir, "data.json")
        self.test_data = {
            "user1": {"name": "Alice", "age": 30},
            "user2": {"name": "Bob", "age": 25},
            "user3": {"name": "Charlie", "age": 35},
        }
        with open(self.json_file, "w") as f:
            json.dump(self.test_data, f)

    def tearDown(self):
        """Clean up temporary files."""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_enumerate_dict(self):
        """JSON dict should yield one item per key."""
        source = JsonSource("test", {"path": self.json_file})
        items = list(source.enumerate_items())
        self.assertEqual(len(items), 3)
        paths = [item["path"] for item in items]
        self.assertIn("user1", paths)
        self.assertIn("user2", paths)
        self.assertIn("user3", paths)

    def test_enumerate_list(self):
        """JSON list should yield one item per element."""
        list_file = os.path.join(self.tmpdir, "list.json")
        with open(list_file, "w") as f:
            json.dump([{"id": 1}, {"id": 2}], f)
        source = JsonSource("test", {"path": list_file})
        items = list(source.enumerate_items())
        self.assertEqual(len(items), 2)

    def test_item_hash(self):
        """Hash should be consistent for the same content."""
        source = JsonSource("test", {"path": self.json_file})
        items = list(source.enumerate_items())
        hash1 = source.get_item_hash(items[0])
        hash2 = source.get_item_hash(items[0])
        self.assertEqual(hash1, hash2)

    def test_nonexistent_file(self):
        """Non-existent file should yield no items."""
        source = JsonSource("test", {"path": "/nonexistent.json"})
        items = list(source.enumerate_items())
        self.assertEqual(len(items), 0)


class TestCsvSource(unittest.TestCase):
    """Tests for the CsvSource adapter."""

    def setUp(self):
        """Create a temporary CSV file."""
        self.tmpdir = tempfile.mkdtemp()
        self.csv_file = os.path.join(self.tmpdir, "data.csv")
        with open(self.csv_file, "w", newline="") as f:
            f.write("id,name,value\n")
            f.write("1,Alice,100\n")
            f.write("2,Bob,200\n")
            f.write("3,Charlie,300\n")

    def tearDown(self):
        """Clean up temporary files."""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_enumerate_rows(self):
        """CSV file should yield one item per row."""
        source = CsvSource("test", {"path": self.csv_file})
        items = list(source.enumerate_items())
        self.assertEqual(len(items), 3)

    def test_key_field(self):
        """Using a key_field should use that column for item paths."""
        source = CsvSource("test", {"path": self.csv_file, "key_field": "name"})
        items = list(source.enumerate_items())
        paths = [item["path"] for item in items]
        self.assertIn("Alice", paths)
        self.assertIn("Bob", paths)
        self.assertIn("Charlie", paths)

    def test_item_hash(self):
        """Hash should be consistent for the same content."""
        source = CsvSource("test", {"path": self.csv_file})
        items = list(source.enumerate_items())
        hash1 = source.get_item_hash(items[0])
        hash2 = source.get_item_hash(items[0])
        self.assertEqual(hash1, hash2)

    def test_nonexistent_file(self):
        """Non-existent file should yield no items."""
        source = CsvSource("test", {"path": "/nonexistent.csv"})
        items = list(source.enumerate_items())
        self.assertEqual(len(items), 0)


class TestSafeJsonIO(unittest.TestCase):
    """Tests for safe JSON read/write utilities."""

    def setUp(self):
        """Create a temporary directory."""
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files."""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_safe_read_missing(self):
        """Reading a missing file should return the default."""
        result = safe_read_json("/nonexistent/file.json", default={"key": "val"})
        self.assertEqual(result, {"key": "val"})

    def test_safe_write_and_read(self):
        """Written data should be readable."""
        filepath = os.path.join(self.tmpdir, "test.json")
        data = {"hello": "world", "count": 42}
        safe_write_json(filepath, data)
        result = safe_read_json(filepath)
        self.assertEqual(result, data)

    def test_safe_write_creates_directories(self):
        """Writing should create parent directories."""
        filepath = os.path.join(self.tmpdir, "sub", "dir", "test.json")
        safe_write_json(filepath, {"test": True})
        self.assertTrue(os.path.isfile(filepath))


class TestSyncEngineBasic(unittest.TestCase):
    """Basic tests for the SyncEngine."""

    def setUp(self):
        """Create temporary directories for source and target."""
        self.tmpdir = tempfile.mkdtemp()
        self.source_dir = os.path.join(self.tmpdir, "source")
        self.target_dir = os.path.join(self.tmpdir, "target")
        self.storage_path = os.path.join(self.tmpdir, "index.json")
        os.makedirs(self.source_dir)
        os.makedirs(self.target_dir)

        # Create source files
        with open(os.path.join(self.source_dir, "file1.txt"), "w") as f:
            f.write("content 1")
        with open(os.path.join(self.source_dir, "file2.txt"), "w") as f:
            f.write("content 2")

        # Create config
        config_data = dict(DEFAULT_CONFIG)
        config_data["index"]["storage_path"] = self.storage_path
        config_data["sources"] = [
            {
                "name": "test_src",
                "type": "filesystem",
                "path": self.source_dir,
                "recursive": False,
            }
        ]
        self.config = SyncIndexConfig(config_data)

    def tearDown(self):
        """Clean up temporary files."""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_dry_run_sync(self):
        """Dry-run sync should not create files in target."""
        from syncindex.sync_engine import SyncEngine
        engine = SyncEngine(self.config)
        result = engine.sync(dry_run=True, target_dir=self.target_dir)
        self.assertTrue(result.dry_run)
        # Target should remain empty
        target_files = os.listdir(self.target_dir)
        self.assertEqual(len(target_files), 0)

    def test_live_sync(self):
        """Live sync should copy files to target."""
        from syncindex.sync_engine import SyncEngine
        engine = SyncEngine(self.config)
        result = engine.sync(dry_run=False, target_dir=self.target_dir)
        self.assertTrue(result.success)
        self.assertGreater(result.total_synced, 0)
        # Target should have files
        target_files = os.listdir(self.target_dir)
        self.assertIn("file1.txt", target_files)
        self.assertIn("file2.txt", target_files)

    def test_incremental_sync(self):
        """Second sync with no changes should report no changes."""
        from syncindex.sync_engine import SyncEngine
        engine = SyncEngine(self.config)
        # First sync
        engine.sync(dry_run=False, target_dir=self.target_dir)
        # Second sync (no changes)
        result = engine.sync(dry_run=False, target_dir=self.target_dir)
        self.assertTrue(result.success)
        if result.diff:
            self.assertEqual(result.diff.total_changes, 0)


class TestReporter(unittest.TestCase):
    """Tests for the report generator."""

    def test_markdown_report(self):
        """Markdown report should be a non-empty string."""
        from syncindex.reporter import generate_report, ReportData
        data = ReportData(
            index_status={"total_entries": 5, "total_size_formatted": "1.2 KB"},
            sync_result={"success": True, "duration": 1.5, "synced_added": 2},
        )
        report = generate_report(data, "markdown")
        self.assertIsInstance(report, str)
        self.assertIn("SyncIndex Report", report)

    def test_json_report(self):
        """JSON report should be valid JSON."""
        from syncindex.reporter import generate_report, ReportData
        data = ReportData()
        report = generate_report(data, "json")
        parsed = json.loads(report)
        self.assertIsInstance(parsed, dict)

    def test_csv_report(self):
        """CSV report should have header row."""
        from syncindex.reporter import generate_report, ReportData
        data = ReportData()
        report = generate_report(data, "csv")
        self.assertIn("path", report)

    def test_save_report(self):
        """Saved report should exist on disk."""
        from syncindex.reporter import save_report, ReportData
        tmpdir = tempfile.mkdtemp()
        try:
            data = ReportData()
            filepath = save_report(data, tmpdir, "markdown")
            self.assertTrue(os.path.isfile(filepath))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
