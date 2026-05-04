"""
Utility functions for SyncIndex.

Provides file hashing, path matching, human-readable formatting,
and colored terminal output helpers. All implementations use only
the Python standard library.
"""

import fnmatch
import hashlib
import os
import sys
import time


# ---------------------------------------------------------------------------
# File hashing
# ---------------------------------------------------------------------------

def compute_file_hash(filepath, algorithm="sha256", block_size=65536):
    """Compute the hash of a file using the specified algorithm.

    Supports ``md5``, ``sha1``, and ``sha256``.  The file is read in
    chunks of *block_size* bytes so that large files can be hashed
    without excessive memory usage.

    Args:
        filepath: Absolute or relative path to the file.
        algorithm: Hash algorithm name (``md5``, ``sha1``, ``sha256``).
        block_size: Number of bytes to read per iteration.

    Returns:
        Hexadecimal hash string.

    Raises:
        ValueError: If *algorithm* is not supported.
        FileNotFoundError: If *filepath* does not exist.
    """
    algorithm = algorithm.lower()
    if algorithm not in ("md5", "sha1", "sha256"):
        raise ValueError(
            f"Unsupported hash algorithm '{algorithm}'. "
            "Choose from: md5, sha1, sha256"
        )

    hasher = hashlib.new(algorithm)
    with open(filepath, "rb") as fh:
        while True:
            data = fh.read(block_size)
            if not data:
                break
            hasher.update(data)
    return hasher.hexdigest()


def compute_bytes_hash(data, algorithm="sha256"):
    """Compute the hash of raw bytes.

    Args:
        data: Bytes-like object.
        algorithm: Hash algorithm name (``md5``, ``sha1``, ``sha256``).

    Returns:
        Hexadecimal hash string.
    """
    algorithm = algorithm.lower()
    if algorithm not in ("md5", "sha1", "sha256"):
        raise ValueError(
            f"Unsupported hash algorithm '{algorithm}'. "
            "Choose from: md5, sha1, sha256"
        )
    return hashlib.new(algorithm, data).hexdigest()


# ---------------------------------------------------------------------------
# Path matching
# ---------------------------------------------------------------------------

def match_patterns(path, patterns):
    """Check whether *path* matches any of the given glob *patterns*.

    Matching is case-insensitive on Windows and case-sensitive on
    other platforms.

    Args:
        path: The file path to test.
        patterns: A list of glob patterns (e.g. ``["*.pyc", "__pycache__"]``).

    Returns:
        ``True`` if *path* matches at least one pattern, else ``False``.
    """
    if not patterns:
        return False
    basename = os.path.basename(path)
    for pattern in patterns:
        if fnmatch.fnmatch(basename, pattern):
            return True
        # Also try matching the full relative path
        if fnmatch.fnmatch(path, pattern):
            return True
    return False


def is_path_excluded(path, include_patterns=None, exclude_patterns=None):
    """Determine whether a path should be excluded based on include/exclude rules.

    If *include_patterns* is provided and non-empty, the path must match at
    least one include pattern to be accepted.  If *exclude_patterns* is
    provided, any match causes the path to be rejected.

    Args:
        path: The file path to evaluate.
        include_patterns: Optional list of glob patterns that must match.
        exclude_patterns: Optional list of glob patterns that reject.

    Returns:
        ``True`` if the path should be excluded, ``False`` otherwise.
    """
    # Exclude takes priority
    if exclude_patterns and match_patterns(path, exclude_patterns):
        return True

    # If include patterns are defined, path must match at least one
    if include_patterns and not match_patterns(path, include_patterns):
        return True

    return False


# ---------------------------------------------------------------------------
# Human-readable formatting
# ---------------------------------------------------------------------------

def format_size(size_bytes):
    """Convert a byte count into a human-readable string.

    Args:
        size_bytes: Integer number of bytes.

    Returns:
        A string such as ``"1.23 MB"``.
    """
    if size_bytes < 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    index = 0
    value = float(size_bytes)
    while value >= 1024.0 and index < len(units) - 1:
        value /= 1024.0
        index += 1
    if index == 0:
        return f"{int(value)} {units[index]}"
    return f"{value:.2f} {units[index]}"


def format_duration(seconds):
    """Format a duration in seconds into a human-readable string.

    Args:
        seconds: Floating-point number of seconds.

    Returns:
        A string such as ``"1m 23s"`` or ``"0.45s"``.
    """
    if seconds < 0:
        seconds = 0.0
    if seconds < 1.0:
        return f"{seconds:.2f}s"
    minutes = int(seconds) // 60
    secs = seconds - minutes * 60
    if minutes == 0:
        return f"{secs:.1f}s"
    return f"{minutes}m {secs:.1f}s"


def format_timestamp(ts):
    """Format a Unix timestamp as a human-readable local time string.

    Args:
        ts: Floating-point Unix timestamp.

    Returns:
        String in ``YYYY-MM-DD HH:MM:SS`` format.
    """
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


# ---------------------------------------------------------------------------
# Colored terminal output
# ---------------------------------------------------------------------------

class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"


def colored(text, color):
    """Wrap *text* with an ANSI color code.

    If stdout is not a TTY (e.g. piped output), the text is returned
    unchanged so that log files remain readable.

    Args:
        text: The string to colorize.
        color: An ANSI escape sequence from :class:`Colors`.

    Returns:
        The colorized string (or plain *text* when not on a TTY).
    """
    if not sys.stdout.isatty():
        return text
    return f"{color}{text}{Colors.RESET}"


def success(msg):
    """Print a success message with green coloring."""
    print(f"  {colored('[OK]', Colors.GREEN)} {msg}")


def error(msg):
    """Print an error message with red coloring."""
    print(f"  {colored('[ERROR]', Colors.RED)} {msg}")


def warning(msg):
    """Print a warning message with yellow coloring."""
    print(f"  {colored('[WARN]', Colors.YELLOW)} {msg}")


def info(msg):
    """Print an informational message with blue coloring."""
    print(f"  {colored('[INFO]', Colors.BLUE)} {msg}")


def header(msg):
    """Print a section header with bold cyan coloring."""
    width = 60
    print()
    print(colored("=" * width, Colors.CYAN))
    print(colored(f"  {msg}", Colors.BOLD + Colors.CYAN))
    print(colored("=" * width, Colors.CYAN))
    print()


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

def ensure_directory(filepath):
    """Ensure the parent directory of *filepath* exists.

    Args:
        filepath: Path whose parent directory should be created.
    """
    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)


def safe_read_json(filepath, default=None):
    """Read a JSON file, returning *default* on any error.

    Args:
        filepath: Path to the JSON file.
        default: Value to return if the file cannot be read or parsed.

    Returns:
        Parsed JSON data, or *default*.
    """
    import json
    if default is None:
        default = {}
    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def safe_write_json(filepath, data, indent=2):
    """Write data to a JSON file atomically.

    The file is first written to a temporary file in the same directory,
    then renamed to avoid partial writes.

    Args:
        filepath: Destination path.
        data: Data to serialize.
        indent: JSON indentation level.
    """
    import json
    import tempfile
    ensure_directory(filepath)
    fd, tmp_path = tempfile.mkstemp(
        dir=os.path.dirname(filepath) or ".",
        prefix=".syncindex_tmp_",
        suffix=".json",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=indent, ensure_ascii=False)
        os.replace(tmp_path, filepath)
    except Exception:
        # Clean up the temp file on error
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
