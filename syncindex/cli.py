"""
Command-line interface for SyncIndex.

Provides the main entry point and subcommands for the sync tool:

- ``sync``     -- Execute incremental synchronization
- ``watch``    -- Real-time file system monitoring
- ``status``   -- Display current index status
- ``init``     -- Generate a default configuration file
- ``report``   -- Generate a synchronization report
"""

import argparse
import os
import sys

from . import __version__
from .config import load_config, generate_default_config, SyncIndexConfig
from .indexer import Indexer
from .sync_engine import SyncEngine
from .watcher import Watcher
from .reporter import ReportData, save_report, generate_report
from .utils import (
    colored,
    Colors,
    header,
    success,
    error,
    warning,
    info,
)


def build_parser():
    """Build the argument parser for the SyncIndex CLI.

    Returns:
        A configured :class:`argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(
        prog="syncindex",
        description="SyncIndex - Lightweight incremental data synchronization and indexing engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  syncindex init                        Create a default config file
  syncindex sync                        Run incremental sync
  syncindex sync --dry-run              Preview changes without modifying files
  syncindex watch                       Monitor for changes in real-time
  syncindex status                      Show current index status
  syncindex report --format json        Generate a JSON report
  syncindex sync --config myconf.json   Use a custom config file
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"SyncIndex v{__version__}",
    )

    parser.add_argument(
        "--config", "-c",
        default="syncindex.json",
        help="Path to the configuration file (default: syncindex.json)",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Enable verbose output",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # -- init --
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize a default configuration file",
    )
    init_parser.add_argument(
        "--output", "-o",
        default="syncindex.json",
        help="Output path for the config file (default: syncindex.json)",
    )
    init_parser.add_argument(
        "--force", "-f",
        action="store_true",
        default=False,
        help="Overwrite existing config file",
    )

    # -- sync --
    sync_parser = subparsers.add_parser(
        "sync",
        help="Execute incremental synchronization",
    )
    sync_parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        default=False,
        help="Preview changes without modifying files",
    )
    sync_parser.add_argument(
        "--target", "-t",
        default=None,
        help="Target directory for synchronized files",
    )

    # -- watch --
    watch_parser = subparsers.add_parser(
        "watch",
        help="Monitor file system for changes in real-time",
    )
    watch_parser.add_argument(
        "--interval", "-i",
        type=float,
        default=None,
        help="Polling interval in seconds (overrides config)",
    )

    # -- status --
    status_parser = subparsers.add_parser(
        "status",
        help="Display current index status",
    )
    status_parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        dest="json_output",
        help="Output status in JSON format",
    )

    # -- report --
    report_parser = subparsers.add_parser(
        "report",
        help="Generate a synchronization report",
    )
    report_parser.add_argument(
        "--format", "-f",
        default=None,
        choices=["markdown", "json", "csv"],
        help="Report format (default: from config or markdown)",
    )
    report_parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file path for the report",
    )

    return parser


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def cmd_init(args):
    """Handle the ``init`` subcommand.

    Creates a default configuration file at the specified path.

    Args:
        args: Parsed command-line arguments.
    """
    output_path = args.output

    if os.path.exists(output_path) and not args.force:
        error(f"Configuration file already exists: {output_path}")
        info("Use --force to overwrite.")
        return 1

    path = generate_default_config(output_path)
    success(f"Configuration file created: {path}")
    info("Edit the file to configure your data sources, then run:")
    info("  syncindex sync")
    return 0


def cmd_sync(args):
    """Handle the ``sync`` subcommand.

    Loads configuration, builds the index, detects changes, and
    applies the synchronization.

    Args:
        args: Parsed command-line arguments.
    """
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        error(f"Configuration file not found: {args.config}")
        info("Run 'syncindex init' to create a default configuration.")
        return 1
    except Exception as exc:
        error(f"Failed to load configuration: {exc}")
        return 1

    header("Incremental Sync")

    if args.dry_run:
        warning("DRY-RUN MODE: No files will be modified.")

    engine = SyncEngine(config)

    # Progress callback for verbose mode
    if args.verbose:
        def progress_cb(message, progress):
            bar_len = 30
            filled = int(bar_len * progress)
            bar = "=" * filled + "-" * (bar_len - filled)
            sys.stdout.write(f"\r  [{bar}] {progress:.0%} {message}")
            sys.stdout.flush()
            if progress >= 1.0:
                print()
        engine.set_progress_callback(progress_cb)

    result = engine.sync(dry_run=args.dry_run, target_dir=args.target)

    # Print summary
    print(result.summary())

    return 0 if result.success else 1


def cmd_watch(args):
    """Handle the ``watch`` subcommand.

    Starts the file system watcher for real-time monitoring.

    Args:
        args: Parsed command-line arguments.
    """
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        error(f"Configuration file not found: {args.config}")
        info("Run 'syncindex init' to create a default configuration.")
        return 1
    except Exception as exc:
        error(f"Failed to load configuration: {exc}")
        return 1

    watcher = Watcher(
        config,
        interval=args.interval,
    )
    watcher.watch()
    return 0


def cmd_status(args):
    """Handle the ``status`` subcommand.

    Displays the current index status and statistics.

    Args:
        args: Parsed command-line arguments.
    """
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        error(f"Configuration file not found: {args.config}")
        info("Run 'syncindex init' to create a default configuration.")
        return 1
    except Exception as exc:
        error(f"Failed to load configuration: {exc}")
        return 1

    indexer = Indexer(config)
    status = indexer.get_status()

    if args.json_output:
        import json
        print(json.dumps(status, indent=2, ensure_ascii=False))
        return 0

    header("Index Status")

    print(f"  Storage path:   {status['storage_path']}")
    print(f"  Hash algorithm: {status['hash_algorithm']}")
    print(f"  Index exists:   {'Yes' if status['index_exists'] else 'No'}")
    print(f"  Total entries:  {status['total_entries']}")
    print(f"  Total size:     {status['total_size_formatted']}")

    if status["sources"]:
        print()
        print(f"  {'Source':<30} {'Entries':>10}")
        print(f"  {'-' * 30} {'-' * 10}")
        for name, count in sorted(status["sources"].items()):
            print(f"  {name:<30} {count:>10}")

    if not status["index_exists"]:
        print()
        warning("No index found. Run 'syncindex sync' to build the initial index.")

    print()
    return 0


def cmd_report(args):
    """Handle the ``report`` subcommand.

    Generates a synchronization report in the specified format.

    Args:
        args: Parsed command-line arguments.
    """
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        error(f"Configuration file not found: {args.config}")
        info("Run 'syncindex init' to create a default configuration.")
        return 1
    except Exception as exc:
        error(f"Failed to load configuration: {exc}")
        return 1

    header("Generating Report")

    # Gather data
    indexer = Indexer(config)
    index_status = indexer.get_status()

    # Load the last sync result if available
    sync_result = {}
    index_data_file = os.path.join(
        os.path.dirname(config.storage_path) or ".syncindex",
        "last_sync.json",
    )
    from .utils import safe_read_json
    sync_result = safe_read_json(index_data_file, default={})

    fmt = args.format or config.report_format
    report_data = ReportData(
        config=config,
        index_status=index_status,
        sync_result=sync_result,
    )

    if args.output:
        # Save to file
        filepath = save_report(
            report_data,
            output_dir=os.path.dirname(args.output) or config.report_dir,
            fmt=fmt,
            filename=os.path.basename(args.output),
        )
        success(f"Report saved to: {filepath}")
    else:
        # Print to stdout
        content = generate_report(report_data, fmt)
        print(content)

    return 0


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

COMMAND_HANDLERS = {
    "init": cmd_init,
    "sync": cmd_sync,
    "watch": cmd_watch,
    "status": cmd_status,
    "report": cmd_report,
}


def main(argv=None):
    """Main entry point for the SyncIndex CLI.

    Parses command-line arguments and dispatches to the appropriate
    subcommand handler.

    Args:
        argv: Optional list of command-line arguments.  If ``None``,
            ``sys.argv[1:]`` is used.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    handler = COMMAND_HANDLERS.get(args.command)
    if handler is None:
        error(f"Unknown command: {args.command}")
        parser.print_help()
        return 1

    try:
        return handler(args)
    except KeyboardInterrupt:
        print()
        info("Interrupted by user.")
        return 130
    except Exception as exc:
        error(f"Unexpected error: {exc}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
