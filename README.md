# SyncIndex

Lightweight incremental data synchronization and indexing engine CLI.

- YAML/JSON driven configuration
- Zero external dependencies (Python standard library only)
- Multiple data source support (filesystem, JSON, CSV)
- Real-time file system monitoring
- Incremental change detection with hash + mtime verification

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Initialize a default configuration file
syncindex init

# Run incremental sync
syncindex sync

# Watch for changes in real-time
syncindex watch

# View index status
syncindex status

# Generate a sync report
syncindex report
```

## License

MIT
