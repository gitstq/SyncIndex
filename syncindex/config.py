"""
Configuration engine for SyncIndex.

Parses YAML or JSON configuration files and provides a structured
configuration object.  Since the project has zero external dependencies,
a minimal YAML-like parser is implemented for ``.yaml``/``.yml`` files,
with JSON as the primary/fallback format.
"""

import json
import os
import re

from .utils import warning, info


# ---------------------------------------------------------------------------
# Minimal YAML parser (subset sufficient for SyncIndex config files)
# ---------------------------------------------------------------------------

def _parse_yaml_value(raw):
    """Parse a single YAML scalar value.

    Handles booleans, integers, floats, null, quoted strings, and
    unquoted strings.

    Args:
        raw: The raw string value (already stripped).

    Returns:
        The parsed Python value.
    """
    if not raw:
        return ""

    # Quoted strings
    if (raw.startswith('"') and raw.endswith('"')) or \
       (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]

    lower = raw.lower()
    if lower in ("true", "yes", "on"):
        return True
    if lower in ("false", "no", "off"):
        return False
    if lower in ("null", "~", ""):
        return None

    # Integer
    try:
        return int(raw)
    except ValueError:
        pass

    # Float
    try:
        return float(raw)
    except ValueError:
        pass

    return raw


def _parse_yaml(text):
    """Parse a simple YAML document into a Python dict.

    This is a minimal parser that handles the subset of YAML used by
    SyncIndex configuration files.  It supports:

    - Key-value pairs (``key: value``)
    - Nested mappings via indentation
    - Lists (``- item``)
    - Comments (``# ...``)
    - Quoted and unquoted scalar values

    For complex YAML files, users should use the ``.json`` format instead.

    Args:
        text: The YAML document as a string.

    Returns:
        A Python dict representing the parsed YAML.
    """
    lines = text.splitlines()
    root = {}
    stack = [(root, -1)]  # (dict, indent_level)

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        # Calculate indentation
        indent = len(line) - len(line.lstrip())

        # Pop stack until we find the right parent level
        while len(stack) > 1 and stack[-1][1] >= indent:
            stack.pop()

        parent_dict, parent_indent = stack[-1]

        # List item
        if stripped.startswith("- "):
            item_value = stripped[2:].strip()
            # Remove inline comment
            if " #" in item_value:
                item_value = item_value[:item_value.index(" #")].strip()

            # Check if this is a list of mappings (e.g. "- key: value")
            if ": " in item_value:
                # This is a mapping inside a list
                key, val = item_value.split(": ", 1)
                key = key.strip()
                val = _parse_yaml_value(val.strip())
                item_dict = {key: val}
            else:
                item_dict = _parse_yaml_value(item_value)

            # Find or create the list in the parent
            # Lists are identified by the key on the previous non-list line
            # We need to look back for the key
            # Actually, let's handle this differently:
            # If the parent has a key whose value should be a list,
            # we append to it.  We use a heuristic: the last key added
            # to the parent that doesn't have a value yet.
            list_key = None
            for k, v in parent_dict.items():
                if isinstance(v, list):
                    list_key = k

            if list_key is not None:
                parent_dict[list_key].append(item_dict)
            else:
                # Try to find the key from the previous line context
                # Look backwards for a line with a key at indent level
                for j in range(i - 1, -1, -1):
                    prev = lines[j].strip()
                    prev_indent = len(lines[j]) - len(lines[j].lstrip())
                    if prev and not prev.startswith("#") and ": " in prev and prev_indent < indent:
                        pk = prev.split(": ")[0].strip()
                        if pk in parent_dict and isinstance(parent_dict[pk], list):
                            parent_dict[pk].append(item_dict)
                            break
                        elif pk in parent_dict and parent_dict[pk] is None:
                            parent_dict[pk] = [item_dict]
                            break
                else:
                    # Fallback: treat as top-level list item
                    if "__items__" not in parent_dict:
                        parent_dict["__items__"] = []
                    parent_dict["__items__"].append(item_dict)

            i += 1
            continue

        # Key-value pair
        if ": " in stripped or stripped.endswith(":"):
            if stripped.endswith(":") and ": " not in stripped:
                # Key with nested block (value is a dict)
                key = stripped[:-1].strip()
                # Remove inline comment
                if " #" in key:
                    key = key[:key.index(" #")].strip()
                new_dict = {}
                parent_dict[key] = new_dict
                stack.append((new_dict, indent))
            else:
                colon_idx = stripped.index(": ")
                key = stripped[:colon_idx].strip()
                val_str = stripped[colon_idx + 2:].strip()

                # Remove inline comment
                if " #" in val_str:
                    val_str = val_str[:val_str.index(" #")].strip()

                # Check if the value starts a list on the next line
                if val_str == "" or val_str.startswith("["):
                    # Check next non-empty line for list items
                    if val_str == "":
                        # Peek ahead for list items
                        next_idx = i + 1
                        while next_idx < len(lines):
                            next_line = lines[next_idx].strip()
                            if not next_line or next_line.startswith("#"):
                                next_idx += 1
                                continue
                            if next_line.startswith("- "):
                                parent_dict[key] = []
                                stack.append((parent_dict[key], indent))
                                # We'll process list items on next iteration
                                # but we need to store the list reference
                                # Actually, let's use a different approach
                                # Store the list and continue
                                # The list items will be handled above
                                break
                            else:
                                parent_dict[key] = None
                                break
                        if key not in parent_dict:
                            parent_dict[key] = None
                    elif val_str.startswith("[") and val_str.endswith("]"):
                        # Inline list
                        items = val_str[1:-1].split(",")
                        parent_dict[key] = [
                            _parse_yaml_value(item.strip()) for item in items if item.strip()
                        ]
                    else:
                        parent_dict[key] = _parse_yaml_value(val_str)
                else:
                    parent_dict[key] = _parse_yaml_value(val_str)

            i += 1
            continue

        i += 1

    # Clean up __items__ fallback
    if "__items__" in root:
        root = root["__items__"]

    return root


# ---------------------------------------------------------------------------
# Configuration model
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    "version": "1.0",
    "sources": [],
    "index": {
        "hash_algorithm": "sha256",
        "include_patterns": [],
        "exclude_patterns": [
            ".git", "__pycache__", "*.pyc", ".DS_Store",
            "node_modules", ".syncindex"
        ],
        "storage_path": ".syncindex/index.json",
    },
    "sync": {
        "conflict_strategy": "skip",  # skip | overwrite | newer_wins
        "delete_orphans": False,
    },
    "watch": {
        "interval": 2.0,
        "debounce": 0.5,
    },
    "output": {
        "report_dir": ".syncindex/reports",
        "report_format": "markdown",  # markdown | json | csv
    },
}


class SyncIndexConfig:
    """Represents the parsed SyncIndex configuration.

    Attributes:
        version: Configuration schema version.
        sources: List of data source definitions.
        index: Index-related settings.
        sync: Sync-related settings.
        watch: Watch-related settings.
        output: Output/report settings.
        config_path: Path to the loaded config file.
    """

    def __init__(self, data=None, config_path=None):
        """Initialize configuration from a dictionary.

        Args:
            data: Configuration dictionary.  If ``None``, defaults are used.
            config_path: Optional path to the source config file.
        """
        merged = dict(DEFAULT_CONFIG)
        if data:
            self._deep_merge(merged, data)
        self._data = merged
        self.config_path = config_path

    @staticmethod
    def _deep_merge(base, override):
        """Recursively merge *override* into *base*.

        Args:
            base: The base dictionary (modified in-place).
            override: The overriding dictionary.
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                SyncIndexConfig._deep_merge(base[key], value)
            else:
                base[key] = value

    # -- Convenience properties --

    @property
    def version(self):
        """Configuration schema version string."""
        return self._data.get("version", "1.0")

    @property
    def sources(self):
        """List of data source configuration dicts."""
        return self._data.get("sources", [])

    @property
    def index(self):
        """Index settings dict."""
        return self._data.get("index", {})

    @property
    def sync(self):
        """Sync settings dict."""
        return self._data.get("sync", {})

    @property
    def watch(self):
        """Watch settings dict."""
        return self._data.get("watch", {})

    @property
    def output(self):
        """Output settings dict."""
        return self._data.get("output", {})

    @property
    def hash_algorithm(self):
        """Hash algorithm for file indexing (e.g. ``'sha256'``)."""
        return self.index.get("hash_algorithm", "sha256")

    @property
    def include_patterns(self):
        """Glob patterns for files to include."""
        return self.index.get("include_patterns", [])

    @property
    def exclude_patterns(self):
        """Glob patterns for files to exclude."""
        return self.index.get("exclude_patterns", [])

    @property
    def storage_path(self):
        """Path where the index JSON is persisted."""
        return self.index.get("storage_path", ".syncindex/index.json")

    @property
    def conflict_strategy(self):
        """Conflict resolution strategy (``skip``, ``overwrite``, ``newer_wins``)."""
        return self.sync.get("conflict_strategy", "skip")

    @property
    def delete_orphans(self):
        """Whether to delete files in the target that no longer exist in the source."""
        return self.sync.get("delete_orphans", False)

    @property
    def watch_interval(self):
        """File system polling interval in seconds."""
        return self.watch.get("interval", 2.0)

    @property
    def watch_debounce(self):
        """Debounce interval in seconds for watch events."""
        return self.watch.get("debounce", 0.5)

    @property
    def report_dir(self):
        """Directory where reports are saved."""
        return self.output.get("report_dir", ".syncindex/reports")

    @property
    def report_format(self):
        """Default report format (``markdown``, ``json``, ``csv``)."""
        return self.output.get("report_format", "markdown")

    def to_dict(self):
        """Return the full configuration as a plain dictionary.

        Returns:
            A deep copy of the configuration data.
        """
        import copy
        return copy.deepcopy(self._data)


# ---------------------------------------------------------------------------
# Configuration loader
# ---------------------------------------------------------------------------

def load_config(config_path):
    """Load configuration from a YAML or JSON file.

    The format is determined by the file extension:
    - ``.json`` -> parsed with :func:`json.load`
    - ``.yaml`` / ``.yml`` -> parsed with the built-in minimal YAML parser

    Args:
        config_path: Path to the configuration file.

    Returns:
        A :class:`SyncIndexConfig` instance.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If the file format is not recognized.
    """
    config_path = os.path.abspath(config_path)
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as fh:
        text = fh.read()

    ext = os.path.splitext(config_path)[1].lower()

    if ext == ".json":
        data = json.loads(text)
        info(f"Loaded JSON configuration from {config_path}")
    elif ext in (".yaml", ".yml"):
        data = _parse_yaml(text)
        info(f"Loaded YAML configuration from {config_path}")
    else:
        # Try JSON first, then YAML
        try:
            data = json.loads(text)
            info(f"Loaded JSON configuration from {config_path}")
        except json.JSONDecodeError:
            data = _parse_yaml(text)
            info(f"Loaded YAML configuration from {config_path}")

    return SyncIndexConfig(data=data, config_path=config_path)


def generate_default_config(output_path="syncindex.json"):
    """Generate a default configuration file.

    Args:
        output_path: Path where the config file will be written.

    Returns:
        The absolute path of the generated file.
    """
    output_path = os.path.abspath(output_path)
    import copy
    default_data = copy.deepcopy(DEFAULT_CONFIG)

    # Add a sample filesystem source
    default_data["sources"] = [
        {
            "name": "local_files",
            "type": "filesystem",
            "path": "./data",
            "recursive": True,
        }
    ]

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(default_data, fh, indent=2, ensure_ascii=False)

    return output_path
