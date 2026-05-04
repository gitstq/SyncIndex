"""
Report generator for SyncIndex.

Produces synchronization reports in Markdown, JSON, and CSV formats.
Reports include statistics such as file counts, change summaries,
and timing information.
"""

import csv
import io
import json
import os
import time

from .utils import (
    colored,
    Colors,
    format_size,
    format_duration,
    format_timestamp,
    ensure_directory,
    header,
)


class ReportData:
    """Container for all data needed to generate a report.

    Attributes:
        generated_at: Timestamp when the report was generated.
        config: The application configuration object.
        index_status: Dictionary from :meth:`Indexer.get_status`.
        sync_result: Dictionary from :meth:`SyncResult.to_dict`.
        entries: List of index entry dictionaries.
    """

    def __init__(self, config=None, index_status=None, sync_result=None, entries=None):
        """Initialize report data.

        Args:
            config: Application configuration.
            index_status: Index statistics dictionary.
            sync_result: Sync result dictionary.
            entries: List of index entry dicts.
        """
        self.generated_at = time.time()
        self.config = config
        self.index_status = index_status or {}
        self.sync_result = sync_result or {}
        self.entries = entries or []


class MarkdownReporter:
    """Generates Markdown-format sync reports."""

    @staticmethod
    def generate(report_data):
        """Generate a Markdown report.

        Args:
            report_data: A :class:`ReportData` instance.

        Returns:
            The report as a Markdown string.
        """
        lines = []
        lines.append("# SyncIndex Report")
        lines.append("")
        lines.append(f"**Generated:** {format_timestamp(report_data.generated_at)}")
        lines.append("")

        # Index status section
        if report_data.index_status:
            status = report_data.index_status
            lines.append("## Index Status")
            lines.append("")
            lines.append(f"| Metric | Value |")
            lines.append(f"|--------|-------|")
            lines.append(f"| Total entries | {status.get('total_entries', 0)} |")
            lines.append(f"| Total size | {status.get('total_size_formatted', '0 B')} |")
            lines.append(f"| Hash algorithm | {status.get('hash_algorithm', 'N/A')} |")
            lines.append(f"| Index exists | {'Yes' if status.get('index_exists') else 'No'} |")
            lines.append("")

            sources = status.get("sources", {})
            if sources:
                lines.append("### Sources")
                lines.append("")
                lines.append("| Source | Entries |")
                lines.append("|--------|---------|")
                for name, count in sorted(sources.items()):
                    lines.append(f"| {name} | {count} |")
                lines.append("")

        # Sync result section
        if report_data.sync_result:
            sr = report_data.sync_result
            diff = sr.get("diff", {})
            lines.append("## Sync Result")
            lines.append("")
            mode = "Dry-Run" if sr.get("dry_run") else "Live"
            status_text = "Success" if sr.get("success") else "Failed"
            lines.append(f"| Metric | Value |")
            lines.append(f"|--------|-------|")
            lines.append(f"| Mode | {mode} |")
            lines.append(f"| Status | {status_text} |")
            lines.append(f"| Duration | {format_duration(sr.get('duration', 0))} |")
            lines.append(f"| Added | {sr.get('synced_added', 0)} |")
            lines.append(f"| Modified | {sr.get('synced_modified', 0)} |")
            lines.append(f"| Deleted | {sr.get('synced_deleted', 0)} |")
            lines.append(f"| Skipped | {sr.get('skipped', 0)} |")
            lines.append(f"| Errors | {len(sr.get('errors', []))} |")
            lines.append("")

            # Change details
            if diff:
                lines.append("### Change Details")
                lines.append("")

                for change_type in ("added", "modified", "deleted"):
                    items = diff.get(change_type, [])
                    if items:
                        lines.append(f"#### {change_type.capitalize()} ({len(items)})")
                        lines.append("")
                        lines.append("| Path | Source | Size | Hash |")
                        lines.append("|------|--------|------|------|")
                        for item in items:
                            path = item.get("path", "N/A")
                            source = item.get("source", "N/A")
                            size = format_size(item.get("size", 0))
                            hash_val = item.get("hash", "N/A")
                            if len(hash_val) > 16:
                                hash_val = hash_val[:16] + "..."
                            lines.append(f"| `{path}` | {source} | {size} | `{hash_val}` |")
                        lines.append("")

                # Errors
                errors = sr.get("errors", [])
                if errors:
                    lines.append("### Errors")
                    lines.append("")
                    for err in errors:
                        lines.append(f"- {err}")
                    lines.append("")

        # Entry listing
        if report_data.entries:
            lines.append("## Indexed Entries")
            lines.append("")
            lines.append(f"Total: {len(report_data.entries)} entries")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("*Generated by [SyncIndex](https://github.com/syncindex)*")
        lines.append("")

        return "\n".join(lines)


class JsonReporter:
    """Generates JSON-format sync reports."""

    @staticmethod
    def generate(report_data):
        """Generate a JSON report.

        Args:
            report_data: A :class:`ReportData` instance.

        Returns:
            The report as a formatted JSON string.
        """
        data = {
            "generated_at": format_timestamp(report_data.generated_at),
            "index_status": report_data.index_status,
            "sync_result": report_data.sync_result,
            "total_entries": len(report_data.entries),
        }
        return json.dumps(data, indent=2, ensure_ascii=False)


class CsvReporter:
    """Generates CSV-format sync reports."""

    @staticmethod
    def generate(report_data):
        """Generate a CSV report.

        The CSV contains one row per changed entry with columns for
        path, source, change type, size, and hash.

        Args:
            report_data: A :class:`ReportData` instance.

        Returns:
            The report as a CSV string.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["path", "source", "change_type", "size", "hash", "mtime"])

        # Extract changes from sync result
        diff = report_data.sync_result.get("diff", {})
        if diff:
            for change_type in ("added", "modified", "deleted"):
                for item in diff.get(change_type, []):
                    writer.writerow([
                        item.get("path", ""),
                        item.get("source", ""),
                        change_type,
                        item.get("size", 0),
                        item.get("hash", ""),
                        item.get("mtime", ""),
                    ])

        return output.getvalue()


# ---------------------------------------------------------------------------
# Reporter factory
# ---------------------------------------------------------------------------

REPORTER_REGISTRY = {
    "markdown": MarkdownReporter,
    "json": JsonReporter,
    "csv": CsvReporter,
}


def generate_report(report_data, fmt="markdown"):
    """Generate a report in the specified format.

    Args:
        report_data: A :class:`ReportData` instance.
        fmt: Report format (``markdown``, ``json``, ``csv``).

    Returns:
        The report as a string.

    Raises:
        ValueError: If the format is not recognized.
    """
    fmt = fmt.lower()
    reporter_cls = REPORTER_REGISTRY.get(fmt)
    if reporter_cls is None:
        raise ValueError(
            f"Unknown report format '{fmt}'. "
            f"Available: {', '.join(sorted(REPORTER_REGISTRY))}"
        )
    return reporter_cls.generate(report_data)


def save_report(report_data, output_dir, fmt="markdown", filename=None):
    """Generate and save a report to disk.

    Args:
        report_data: A :class:`ReportData` instance.
        output_dir: Directory to write the report to.
        fmt: Report format (``markdown``, ``json``, ``csv``).
        filename: Optional custom filename.  If ``None``, a timestamped
            default name is generated.

    Returns:
        The absolute path of the saved report file.
    """
    ensure_directory(output_dir)
    output_dir = os.path.abspath(output_dir)

    if filename is None:
        ts = time.strftime("%Y%m%d_%H%M%S")
        ext_map = {"markdown": "md", "json": "json", "csv": "csv"}
        ext = ext_map.get(fmt, "txt")
        filename = f"report_{ts}.{ext}"

    filepath = os.path.join(output_dir, filename)
    content = generate_report(report_data, fmt)

    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write(content)

    return filepath
