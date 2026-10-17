"""Summarize synthetic event CSV records."""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_FIELDS = ("timestamp", "level", "service", "message")
OUTPUT_FIELDS = ("level", "service", "message", "count", "first_seen", "last_seen")
TIMESTAMP_PATTERN = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})"
)

GroupKey = tuple[str, str, str]
GroupValue = tuple[int, datetime, datetime]


class LogsumError(Exception):
    """An input or output error suitable for a user-facing diagnostic."""


def _normalize_level(value: str) -> str:
    value = value.strip().upper()
    return value


def _normalize_service(value: str) -> str:
    return value.strip().casefold()


def _normalize_message(value: str) -> str:
    return " ".join(value.split())


def _parse_timestamp(value: str, record_number: int) -> datetime:
    if not TIMESTAMP_PATTERN.fullmatch(value):
        raise LogsumError(f"record {record_number}: invalid timestamp {value!r}")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise LogsumError(
            f"record {record_number}: invalid timestamp {value!r}"
        ) from exc


def _format_timestamp(value: datetime) -> str:
    result = (
        f"{value.year:04d}-{value.month:02d}-{value.day:02d}"
        f"T{value.hour:02d}:{value.minute:02d}:{value.second:02d}"
    )
    if value.microsecond:
        result += f".{value.microsecond:06d}"
    return result + "Z"


def _read_groups(input_path: Path) -> dict[GroupKey, GroupValue]:
    groups: dict[GroupKey, GroupValue] = {}
    header: list[str] | None = None
    columns: dict[str, int] = {}
    record_number = 0

    with input_path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.reader(source, strict=True)
        for row in reader:
            if not row:
                continue
            record_number += 1

            if header is None:
                header = row
                if len(set(header)) != len(header):
                    raise LogsumError("input has duplicate header names")
                missing = sorted(set(REQUIRED_FIELDS) - set(header))
                if missing:
                    raise LogsumError(
                        f"input is missing required header(s): {', '.join(missing)}"
                    )
                columns = {name: header.index(name) for name in REQUIRED_FIELDS}
                continue

            if len(row) != len(header):
                raise LogsumError(
                    f"record {record_number}: expected {len(header)} fields, "
                    f"found {len(row)}"
                )

            timestamp = _parse_timestamp(row[columns["timestamp"]], record_number)
            key = (
                _normalize_level(row[columns["level"]]),
                _normalize_service(row[columns["service"]]),
                _normalize_message(row[columns["message"]]),
            )
            previous = groups.get(key)
            if previous is None:
                groups[key] = (1, timestamp, timestamp)
            else:
                count, first_seen, last_seen = previous
                groups[key] = (
                    count + 1,
                    min(first_seen, timestamp),
                    max(last_seen, timestamp),
                )

    if header is None:
        raise LogsumError("input has no header")
    return groups


def _ensure_distinct_paths(input_path: Path, output_path: Path) -> None:
    if input_path.resolve() == output_path.resolve():
        raise LogsumError("input and output must be different files")
    if (
        input_path.exists()
        and output_path.exists()
        and os.path.samefile(input_path, output_path)
    ):
        raise LogsumError("input and output must be different files")


def _write_summary(
    output_path: Path, groups: dict[GroupKey, GroupValue]
) -> None:
    if not output_path.parent.is_dir():
        raise LogsumError(f"output directory does not exist: {output_path.parent}")

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            dir=output_path.parent,
            delete=False,
        ) as destination:
            temporary_path = Path(destination.name)
            writer = csv.writer(destination, lineterminator="\n")
            writer.writerow(OUTPUT_FIELDS)
            for key in sorted(groups):
                count, first_seen, last_seen = groups[key]
                writer.writerow(
                    (
                        *key,
                        count,
                        _format_timestamp(first_seen),
                        _format_timestamp(last_seen),
                    )
                )
        os.replace(temporary_path, output_path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Count normalized groups in a synthetic events CSV."
    )
    parser.add_argument("paths", nargs="*", metavar="PATH")
    parser.add_argument("--input", dest="input_option")
    parser.add_argument("--output", dest="output_option")
    args = parser.parse_args(argv)

    if args.paths:
        if (
            len(args.paths) != 2
            or args.input_option is not None
            or args.output_option is not None
        ):
            parser.error("provide either two positional paths or --input/--output")
        input_path, output_path = map(Path, args.paths)
    else:
        input_path = Path(args.input_option or "data/events.csv")
        output_path = Path(args.output_option or "summary.csv")

    try:
        _ensure_distinct_paths(input_path, output_path)
        groups = _read_groups(input_path)
        _write_summary(output_path, groups)
    except (
        LogsumError,
        OSError,
        csv.Error,
        UnicodeError,
        ValueError,
        RuntimeError,
    ) as exc:
        print(f"logsum-sandbox: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())