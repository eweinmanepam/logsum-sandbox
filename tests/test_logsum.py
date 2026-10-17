"""Black-box tests for the logsum-sandbox command-line contract."""

from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = next(
    (
        candidate
        for candidate in (Path.cwd(), *Path(__file__).resolve().parents)
        if (candidate / "src").is_dir()
    ),
    Path.cwd(),
)
FIXTURE = Path(__file__).parent / "fixtures" / "events.csv"
OUTPUT_HEADER = ["level", "service", "message", "count", "first_seen", "last_seen"]


def run_cli(*args: str | Path, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run the module with the project available for imports."""
    env = os.environ.copy()
    search_path = str(PROJECT_ROOT)
    if env.get("PYTHONPATH"):
        search_path += os.pathsep + env["PYTHONPATH"]
    env["PYTHONPATH"] = search_path
    return subprocess.run(
        [sys.executable, "-m", "src.logsum", *(str(arg) for arg in args)],
        cwd=cwd or PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def write_csv(path: Path, rows: list[list[str]], *, newline: str = "\n") -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator=newline)
        writer.writerows(rows)


def read_summary(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames or [], list(reader)


def minimal_input(path: Path, data_rows: list[list[str]]) -> None:
    write_csv(path, [["timestamp", "level", "service", "message"], *data_rows])


def test_fixture_normalizes_groups_sorts_and_writes_utf8_csv(tmp_path: Path) -> None:
    output = tmp_path / "summary.csv"

    result = run_cli("--input", FIXTURE, "--output", output)

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    assert output.read_bytes().startswith(b"level,service,message,count,first_seen,last_seen")
    assert not output.read_bytes().startswith(b"\xef\xbb\xbf")
    header, rows = read_summary(output)
    assert header == OUTPUT_HEADER
    assert rows == [
        {
            "level": "ERROR",
            "service": "strasse",
            "message": "Disk FULL !!",
            "count": "3",
            "first_seen": "2026-02-03T01:35:06.120000Z",
            "last_seen": "2026-02-03T01:35:06.130000Z",
        },
        {
            "level": "ERROR",
            "service": "strasse",
            "message": "Disk, full",
            "count": "1",
            "first_seen": "2026-02-03T01:35:06Z",
            "last_seen": "2026-02-03T01:35:06Z",
        },
        {
            "level": "ERROR",
            "service": "strasse",
            "message": "disk full !!",
            "count": "1",
            "first_seen": "2026-02-03T01:35:06Z",
            "last_seen": "2026-02-03T01:35:06Z",
        },
    ]


def test_duplicate_rows_count_independently_and_message_ids_are_preserved(
    tmp_path: Path,
) -> None:
    source = tmp_path / "events.csv"
    output = tmp_path / "summary.csv"
    row = ["2026-01-01T00:00:00Z", "warn", "svc", "request id=17 failed"]
    minimal_input(source, [row, row, [*row[:3], "request id=18 failed"]])

    result = run_cli(source, output)

    assert result.returncode == 0
    _, rows = read_summary(output)
    assert [
        (row["level"], row["service"], row["message"], row["count"])
        for row in rows
    ] == [
        ("WARN", "svc", "request id=17 failed", "2"),
        ("WARN", "svc", "request id=18 failed", "1"),
    ]


def test_blank_level_service_and_message_are_valid(tmp_path: Path) -> None:
    source = tmp_path / "events.csv"
    output = tmp_path / "summary.csv"
    minimal_input(
        source,
        [
            ["2026-01-01T00:00:01Z", " \u2003", " \u00a0", "\u3000\t"],
            ["2026-01-01T00:00:00Z", " \u2003", " \u00a0", "\u3000\t"],
        ],
    )

    result = run_cli("--input", source, "--output", output)

    assert result.returncode == 0
    _, rows = read_summary(output)
    assert rows == [
        {
            "level": "UNKNOWN",
            "service": "",
            "message": "",
            "count": "2",
            "first_seen": "2026-01-01T00:00:00Z",
            "last_seen": "2026-01-01T00:00:01Z",
        }
    ]


def test_first_and_last_seen_use_earliest_and_latest_utc_instants(
    tmp_path: Path,
) -> None:
    source = tmp_path / "events.csv"
    output = tmp_path / "summary.csv"
    minimal_input(
        source,
        [
            ["2025-12-31T23:00:00-03:00", "info", "api", "same event"],
            ["2026-01-01T00:00:00+02:00", "info", "api", "same event"],
            ["2025-12-31T23:00:00Z", "info", "api", "same event"],
        ],
    )

    result = run_cli(source, output)

    assert result.returncode == 0
    _, rows = read_summary(output)
    assert rows == [
        {
            "level": "INFO",
            "service": "api",
            "message": "same event",
            "count": "3",
            "first_seen": "2025-12-31T22:00:00Z",
            "last_seen": "2026-01-01T02:00:00Z",
        }
    ]


def test_groups_sort_by_normalized_level_service_and_message(tmp_path: Path) -> None:
    source = tmp_path / "events.csv"
    output = tmp_path / "summary.csv"
    minimal_input(
        source,
        [
            ["2026-01-01T00:00:00Z", "info", "zeta", "x"],
            ["2026-01-01T00:00:00Z", "error", "beta", "m"],
            ["2026-01-01T00:00:00Z", "error", "alpha", "z"],
            ["2026-01-01T00:00:00Z", "error", "alpha", "a"],
        ],
    )

    result = run_cli(source, output)

    assert result.returncode == 0
    _, rows = read_summary(output)
    assert [
        (row["level"], row["service"], row["message"]) for row in rows
    ] == [
        ("ERROR", "alpha", "a"),
        ("ERROR", "alpha", "z"),
        ("ERROR", "beta", "m"),
        ("INFO", "zeta", "x"),
    ]


def test_non_ascii_message_is_preserved_as_utf8_without_bom(tmp_path: Path) -> None:
    source = tmp_path / "events.csv"
    output = tmp_path / "summary.csv"
    minimal_input(
        source,
        [["2026-01-01T00:00:00Z", "info", "api", "  Café ☃  "]],
    )

    result = run_cli(source, output)

    assert result.returncode == 0
    data = output.read_bytes()
    assert data.startswith(b"level,service,message,count,first_seen,last_seen")
    assert not data.startswith(b"\xef\xbb\xbf")
    assert "Café ☃".encode() in data
    _, rows = read_summary(output)
    assert rows[0]["message"] == "Café ☃"


def test_blank_records_are_ignored_and_header_can_be_reordered(tmp_path: Path) -> None:
    source = tmp_path / "events.csv"
    output = tmp_path / "summary.csv"
    source.write_text(
        "message,level,service,timestamp,extra\n"
        "hello,info,api,2026-01-01T00:00:00Z,x\n"
        "\n"
        "world,info,api,2026-01-01T00:00:01Z,y\n",
        encoding="utf-8",
    )

    result = run_cli(source, output)

    assert result.returncode == 0
    _, rows = read_summary(output)
    assert [row["message"] for row in rows] == ["hello", "world"]


def test_header_only_input_produces_header_only_summary(tmp_path: Path) -> None:
    source = tmp_path / "events.csv"
    output = tmp_path / "summary.csv"
    source.write_text("timestamp,level,service,message\n", encoding="utf-8")

    result = run_cli("--input", source, "--output", output)

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    header, rows = read_summary(output)
    assert header == OUTPUT_HEADER
    assert rows == []


@pytest.mark.parametrize(
    "timestamp",
    [
        "",
        "2026-2-03T00:00:00Z",
        "2026-02-03T00:00Z",
        "2026-02-03T00:00:00",
        "2026-02-03T00:00:00.1234567Z",
        "2026-02-03T00:00:00.Z",
        "2026-02-30T00:00:00Z",
        "2026-01-01T24:00:00Z",
        "2026-01-01T00:00:00z",
        "2026-01-01t00:00:00Z",
        "2026-01-01T00:00:00+0000",
        "2026-01-01T00:00:00,1Z",
        "2026-01-01T00:00:00+24:00",
        " 2026-01-01T00:00:00Z",
    ],
)
def test_invalid_timestamp_reports_csv_record_and_preserves_existing_output(
    tmp_path: Path, timestamp: str
) -> None:
    source = tmp_path / "events.csv"
    output = tmp_path / "summary.csv"
    minimal_input(source, [[timestamp, "error", "svc", "message"]])
    original = b"previous summary\n"
    output.write_bytes(original)

    result = run_cli(source, output)

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.strip()
    assert "2" in result.stderr  # header is record 1; this event is record 2.
    assert output.read_bytes() == original


def test_timestamp_error_uses_csv_record_number_not_physical_line_number(
    tmp_path: Path,
) -> None:
    source = tmp_path / "events.csv"
    output = tmp_path / "summary.csv"
    source.write_text(
        "timestamp,level,service,message\n"
        '2026-01-01T00:00:00Z,info,api,"two\n'
        'physical lines"\n'
        "not-a-time,error,api,bad\n",
        encoding="utf-8",
    )
    output.write_bytes(b"keep me")

    result = run_cli(source, output)

    assert result.returncode == 1
    assert "record 3" in result.stderr.lower()
    assert output.read_bytes() == b"keep me"


@pytest.mark.parametrize(
    ("header", "data"),
    [
        ("timestamp,level,service", "2026-01-01T00:00:00Z,error,api"),
        ("Timestamp,level,service,message", "2026-01-01T00:00:00Z,error,api,x"),
        (
            "timestamp,level,service,message,message",
            "2026-01-01T00:00:00Z,error,api,x,y",
        ),
    ],
)
def test_missing_or_duplicate_header_is_an_input_error_and_atomic(
    tmp_path: Path, header: str, data: str
) -> None:
    source = tmp_path / "events.csv"
    output = tmp_path / "summary.csv"
    source.write_text(f"{header}\n{data}\n", encoding="utf-8")
    output.write_bytes(b"old output")

    result = run_cli(source, output)

    assert result.returncode == 1
    assert result.stderr.strip()
    assert output.read_bytes() == b"old output"


@pytest.mark.parametrize(
    "contents",
    [
        "",
        "timestamp,level,service,message\n2026-01-01T00:00:00Z,error,api\n",
        "timestamp,level,service,message\n2026-01-01T00:00:00Z,error,api,x,extra\n",
        'timestamp,level,service,message\n2026-01-01T00:00:00Z,error,api,"unterminated\n',
        'timestamp,level,service,message\n2026-01-01T00:00:00Z,"error"junk,api,x\n',
    ],
    ids=[
        "zero-byte",
        "too-few-fields",
        "too-many-fields",
        "unterminated-quote",
        "characters-after-closing-quote",
    ],
)
def test_malformed_or_wrong_width_input_fails_without_replacing_output(
    tmp_path: Path, contents: str
) -> None:
    source = tmp_path / "events.csv"
    output = tmp_path / "summary.csv"
    source.write_text(contents, encoding="utf-8")
    output.write_bytes(b"previous output")

    result = run_cli(source, output)

    assert result.returncode == 1
    assert result.stderr.strip()
    assert output.read_bytes() == b"previous output"


def test_missing_input_fails_without_changing_output(tmp_path: Path) -> None:
    output = tmp_path / "summary.csv"
    output.write_bytes(b"previous output")

    result = run_cli(tmp_path / "missing.csv", output)

    assert result.returncode == 1
    assert result.stderr.strip()
    assert output.read_bytes() == b"previous output"


def test_unreadable_input_fails_without_changing_output(tmp_path: Path) -> None:
    input_directory = tmp_path / "events.csv"
    input_directory.mkdir()
    output = tmp_path / "summary.csv"
    output.write_bytes(b"previous output")

    result = run_cli(input_directory, output)

    assert result.returncode == 1
    assert result.stderr.strip()
    assert output.read_bytes() == b"previous output"


def test_utf8_bom_input_is_rejected_as_missing_exact_header(tmp_path: Path) -> None:
    source = tmp_path / "events.csv"
    output = tmp_path / "summary.csv"
    source.write_bytes(
        b"\xef\xbb\xbftimestamp,level,service,message\n"
        b"2026-01-01T00:00:00Z,error,api,message\n"
    )
    output.write_bytes(b"previous output")

    result = run_cli(source, output)

    assert result.returncode == 1
    assert result.stderr.strip()
    assert output.read_bytes() == b"previous output"


def test_same_resolved_input_and_output_path_fails_without_changing_file(
    tmp_path: Path,
) -> None:
    source = tmp_path / "events.csv"
    original = (
        b"timestamp,level,service,message\n"
        b"2026-01-01T00:00:00Z,info,api,valid\n"
    )
    source.write_bytes(original)
    alias = tmp_path / "." / "events.csv"

    result = run_cli("--input", source, "--output", alias)

    assert result.returncode == 1
    assert result.stderr.strip()
    assert source.read_bytes() == original


def test_output_parent_is_not_created(tmp_path: Path) -> None:
    source = tmp_path / "events.csv"
    minimal_input(source, [])
    missing_parent = tmp_path / "absent" / "summary.csv"

    result = run_cli(source, missing_parent)

    assert result.returncode == 1
    assert result.stderr.strip()
    assert not missing_parent.parent.exists()


def test_output_directory_is_an_output_error(tmp_path: Path) -> None:
    source = tmp_path / "events.csv"
    minimal_input(source, [])
    output_directory = tmp_path / "summary.csv"
    output_directory.mkdir()

    result = run_cli(source, output_directory)

    assert result.returncode == 1
    assert result.stderr.strip()


def test_positional_paths_and_flag_paths_are_supported(tmp_path: Path) -> None:
    source = tmp_path / "events.csv"
    minimal_input(source, [["2026-01-01T00:00:00Z", "info", "api", "ok"]])
    positional_output = tmp_path / "positional.csv"
    flag_output = tmp_path / "flags.csv"

    positional = run_cli(source, positional_output)
    flagged = run_cli("--input", source, "--output", flag_output)

    assert positional.returncode == 0
    assert flagged.returncode == 0
    assert read_summary(positional_output) == read_summary(flag_output)


def test_default_paths_are_used_when_flags_are_omitted(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    minimal_input(data_dir / "events.csv", [])

    result = run_cli(cwd=tmp_path)

    assert result.returncode == 0
    assert result.stdout == ""
    header, rows = read_summary(tmp_path / "summary.csv")
    assert header == OUTPUT_HEADER
    assert rows == []


def test_help_prints_usage_and_exits_successfully() -> None:
    result = run_cli("--help")

    assert result.returncode == 0
    assert "usage" in result.stdout.lower()


def test_invalid_arguments_print_usage_to_stderr_and_exit_two() -> None:
    result = run_cli("--unknown-option")

    assert result.returncode == 2
    assert "usage" in result.stderr.lower()


def test_positional_and_flag_forms_cannot_be_mixed(tmp_path: Path) -> None:
    source = tmp_path / "events.csv"
    output = tmp_path / "summary.csv"

    result = run_cli(source, output, "--input", source)

    assert result.returncode == 2
    assert "usage" in result.stderr.lower()
