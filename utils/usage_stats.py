#!/usr/bin/env python3
"""Read-only, full-scan ACC usage reports using Python 3.9+ and OpenSSH.

Example: python3 utils/usage_stats.py --server dev --year 2026 --output ./usage
Offline: add --nginx-log access.log --nginx-log access.log.1.gz --api-log logs.log
Raw IP addresses are never included in reports.
"""

import argparse
import csv
import gzip
import ipaddress
import json
import re
import shlex
import subprocess
import sys
import zlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


SERVERS = {"dev": "acc-dev.biodata.ceitec.cz", "prod": "acc.biodata.ceitec.cz"}
DOCUMENTS = {"/", "/docs", "/setup", "/results", "/calculations", "/files"}
CATEGORIES = ("all", "website_document", "calculation_submission", "example_api", "other")
CLIENT_TYPES = ("web_app", "unmarked", "unknown")
COHORTS = {"website_without_submission": "website_document",
           "examples_without_submission": "example_api"}
API_REQUEST = re.compile(
    r"^(?P<time>\d{4}-\d\d-\d\d[ T]\S+) \[INFO\] Request from "
    r"(?P<ip>.+): (?P<method>[A-Z]+) (?P<url>\S+)\s*$"
)
BOT = re.compile(r"bot|crawler|spider|slurp|bingpreview|headless", re.I)


def date_bounds(year, start_date=None, end_date=None):
    def parse_date(value):
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError("dates must be UTC YYYY-MM-DD")
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    start = parse_date(start_date) if start_date else datetime(year, 1, 1, tzinfo=timezone.utc)
    end = parse_date(end_date) if end_date else datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    if start >= end:
        raise ValueError("start date must precede exclusive end date")
    return start, end


def database_sql(start, end):
    # Bounds are datetime objects, never interpolated CLI text. Only metadata is read.
    def histogram(query, column, bins):
        cases = " ".join(f"WHEN {column} <= {upper} THEN '{label}'" for upper, label in bins)
        labels = [label for _, label in bins] + ["1001+" if column == "molecules" else "10001+", "unknown"]
        values = ", ".join(f"('{label}', {i})" for i, label in enumerate(labels))
        return f"""(SELECT json_agg(json_build_object('bin', b.bin, 'count', COALESCE(h.n, 0)) ORDER BY b.ord)
          FROM (VALUES {values}) b(bin, ord)
          LEFT JOIN (SELECT CASE WHEN {column} IS NULL THEN 'unknown' {cases}
                     ELSE '{labels[-2]}' END AS bin, count(*) AS n
                     FROM {query} GROUP BY 1) h USING (bin))"""

    molecule_hist = histogram("per_set", "molecules", [(0, "0"), (1, "1"), (10, "2-10"),
                                                          (100, "11-100"), (1000, "101-1000")])
    atom_hist = histogram("single_inputs", "atoms", [(0, "0"), (10, "1-10"), (25, "11-25"),
                                                       (50, "26-50"), (100, "51-100"),
                                                       (250, "101-250"), (1000, "251-1000"),
                                                       (10000, "1001-10000")])
    return f"""BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL TIME ZONE 'UTC';
SET LOCAL statement_timeout = '10s';
SET LOCAL lock_timeout = '1s';
WITH scoped AS MATERIALIZED (
  SELECT id, created_at FROM calculation_sets
  WHERE created_at >= '{start.isoformat()}'::timestamptz
    AND created_at < '{end.isoformat()}'::timestamptz
), methods AS (
  SELECT DISTINCT s.id, c.method FROM scoped s
  JOIN calculation_set_configs a ON a.calculation_set_id = s.id
  JOIN calculation_configs c ON c.id = a.config_id WHERE c.method IS NOT NULL
), links AS MATERIALIZED (
  SELECT DISTINCT a.calculation_set_id, a.molecule_set_id FROM calculation_set_stats a
  JOIN scoped s ON s.id = a.calculation_set_id
), inputs AS MATERIALIZED (
  SELECT l.molecule_set_id, m.total_molecules, m.total_atoms
  FROM (SELECT DISTINCT molecule_set_id FROM links) l
  LEFT JOIN molecule_set_stats m ON m.file_hash = l.molecule_set_id
), per_set AS (
  SELECT s.id, count(l.molecule_set_id) AS linked_inputs,
    count(*) FILTER (WHERE l.molecule_set_id IS NOT NULL AND
      (i.total_molecules IS NULL OR i.total_molecules < 0)) AS invalid_inputs,
    CASE WHEN count(l.molecule_set_id) > 0 AND
      count(*) FILTER (WHERE i.total_molecules IS NULL OR i.total_molecules < 0) = 0
      THEN sum(i.total_molecules) END AS molecules
  FROM scoped s LEFT JOIN links l ON l.calculation_set_id = s.id
  LEFT JOIN inputs i ON i.molecule_set_id = l.molecule_set_id GROUP BY s.id
), single_inputs AS (
  SELECT CASE WHEN total_atoms >= 0 THEN total_atoms END AS atoms
  FROM inputs WHERE total_molecules = 1
)
SELECT json_build_object(
  'coverage', json_build_object(
    'retained_sets_all_time', (SELECT count(*) FROM calculation_sets),
    'retained_first_created_at_utc', (SELECT min(created_at) FROM calculation_sets),
    'retained_last_created_at_utc', (SELECT max(created_at) FROM calculation_sets),
    'sets_missing_created_at', (SELECT count(*) FROM calculation_sets WHERE created_at IS NULL),
    'calculation_sets', (SELECT count(*) FROM scoped),
    'first_created_at_utc', (SELECT min(created_at) FROM scoped),
    'last_created_at_utc', (SELECT max(created_at) FROM scoped),
    'sets_with_methods', (SELECT count(DISTINCT id) FROM methods),
    'sets_without_method_metadata', (SELECT count(*) FROM scoped s WHERE NOT EXISTS (SELECT 1 FROM methods m WHERE m.id = s.id)),
    'sets_without_input_metadata', (SELECT count(*) FROM per_set WHERE linked_inputs = 0),
    'sets_with_invalid_linked_molecule_counts', (SELECT count(*) FROM per_set WHERE invalid_inputs > 0),
    'set_input_associations', (SELECT count(*) FROM links),
    'distinct_linked_input_hashes', (SELECT count(*) FROM inputs),
    'linked_inputs_missing_or_invalid_molecule_counts', (SELECT count(*) FROM inputs WHERE total_molecules IS NULL OR total_molecules < 0),
    'linked_inputs_missing_or_invalid_atom_counts', (SELECT count(*) FROM inputs WHERE total_atoms IS NULL OR total_atoms < 0)),
  'methods_per_calculation_set', (SELECT COALESCE(json_agg(json_build_object('method', method, 'calculation_sets', n) ORDER BY n DESC, method), '[]'::json)
    FROM (SELECT method, count(*) AS n FROM methods GROUP BY method) m),
  'molecules_per_set', json_build_object(
    'known_sets', (SELECT count(molecules) FROM per_set),
    'unknown_sets', (SELECT count(*) FROM per_set WHERE molecules IS NULL),
    'known_molecule_occurrences', (SELECT COALESCE(sum(molecules), 0) FROM per_set),
    'minimum', (SELECT min(molecules) FROM per_set),
    'median', (SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY molecules) FROM per_set),
    'mean', (SELECT avg(molecules) FROM per_set),
    'maximum', (SELECT max(molecules) FROM per_set),
    'histogram', {molecule_hist}),
  'linked_input_atom_sizes', json_build_object(
    'known_molecules', (SELECT COALESCE(sum(total_molecules), 0) FROM inputs WHERE total_molecules >= 0),
    'resolved_single_molecules', (SELECT count(atoms) FROM single_inputs),
    'single_molecules_unknown_atoms', (SELECT count(*) FROM single_inputs WHERE atoms IS NULL),
    'unresolved_multi_molecule_inputs', (SELECT count(*) FROM inputs WHERE total_molecules > 1),
    'unresolved_multi_molecule_count', (SELECT COALESCE(sum(total_molecules), 0) FROM inputs WHERE total_molecules > 1),
    'histogram', {atom_hist})
);
ROLLBACK;
"""


def collect_database(start, end):
    # acc-db is the fixed container_name of service db in deployment/docker-compose.yml.
    # The fixed shell script expands container environment only, not user-supplied text.
    command = ["docker", "exec", "-i", "acc-db", "sh", "-c",
               'exec psql -X -q -A -t -w -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"']
    try:
        completed = subprocess.run(command, input=database_sql(start, end), text=True,
                                   capture_output=True, timeout=30, check=True)
        data = json.loads(completed.stdout)
        if not isinstance(data, dict) or not all(isinstance(data.get(k), t) for k, t in (
            ("coverage", dict), ("methods_per_calculation_set", list),
            ("molecules_per_set", dict), ("linked_input_atom_sizes", dict))):
            raise ValueError("invalid aggregate response")
        if not isinstance(data["coverage"].get("calculation_sets"), int):
            raise ValueError("missing coverage")
        for key in ("molecules_per_set", "linked_input_atom_sizes"):
            rows = data[key].get("histogram")
            if not isinstance(rows, list) or not rows or not all(
                isinstance(row, dict) and isinstance(row.get("bin"), str)
                and type(row.get("count")) is int and row["count"] >= 0 for row in rows
            ):
                raise ValueError("invalid histogram")
        if not all(isinstance(row, dict) and isinstance(row.get("method"), str)
                   and type(row.get("calculation_sets")) is int
                   and row["calculation_sets"] >= 0 for row in data["methods_per_calculation_set"]):
            raise ValueError("invalid methods")
        return {"status": "available", "warnings": [], **data}
    except (OSError, ValueError, subprocess.SubprocessError):
        # Do not echo command output: authentication/server errors may contain secrets.
        return {"status": "unavailable", "warnings": [
            "Database aggregates unavailable (connection, timeout, schema or protocol failure); counts are unknown, not zero"]}


def timestamp(value, assume_utc=False):
    result = datetime.fromisoformat(value.replace("Z", "+00:00").replace(",", "."))
    if result.tzinfo is None:
        if not assume_utc:
            raise ValueError("nginx timestamps must include a timezone")
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def category(method, url):
    path = urlsplit(url).path
    if method == "GET" and path in DOCUMENTS:
        return "website_document"
    if path.startswith("/api/"):
        path = path[4:]
    if method == "POST" and path == "/v1/charges/calculate":
        return "calculation_submission"
    if method == "GET" and (
        re.fullmatch(r"/v1/charges/examples/[^/]+/(molecules|mmcif)", path)
        or re.fullmatch(r"/v1/files/download/examples/[^/]+", path)
    ):
        return "example_api"
    return "other"


def parse(source, line):
    if source == "api":
        if "Request from " not in line:
            return None
        match = API_REQUEST.fullmatch(line)
        if not match:
            raise ValueError("invalid API request line")
        item = match.groupdict()
        return timestamp(item["time"], assume_utc=True), item["ip"], item["method"], item["url"], None, False, None
    item = json.loads(line)
    if not isinstance(item, dict):
        raise ValueError("expected JSON object")
    for key in ("time", "ip", "method", "path"):
        if not isinstance(item.get(key), str) or not item[key]:
            raise ValueError("missing request field")
    status = item["status"]
    if isinstance(status, bool) or not re.fullmatch(r"[1-5][0-9]{2}", str(status)):
        raise ValueError("invalid status")
    ua = item.get("user_agent", "")
    if not isinstance(ua, str):
        raise ValueError("invalid user agent")
    client = item.get("acc_client", "unknown")
    if not isinstance(client, str):
        raise ValueError("invalid client marker")
    if "acc_client" in item and not client:
        client = "unmarked"
    return (timestamp(item["time"]), item["ip"], item["method"], item["path"],
            int(status), bool(BOT.search(ua)), client)


def bucket():
    return {"requests": Counter(), "statuses": Counter(), "ips": {k: set() for k in CATEGORIES},
            "public_ips": {k: set() for k in CATEGORIES},
            "non_bot_ips": {k: set() for k in CATEGORIES},
            "non_bot_public_ips": {k: set() for k in CATEGORIES},
            "known_bot_requests": Counter(),
            "client_types": {name: {"requests": Counter(), "ips": set(),
                                    "public_ips": set(), "calculation_submissions": 0}
                             for name in CLIENT_TYPES},
            "non_public_ip_requests": 0, "invalid_ip_requests": 0,
            "calculation_http_2xx": 0}


def add(target, kind, address, status, bot, client=None):
    for key in ("all", kind):
        target["requests"][key] += 1
        if address is not None:
            target["ips"][key].add(str(address))
            if address.is_global:
                target["public_ips"][key].add(str(address))
            if bot is False:
                target["non_bot_ips"][key].add(str(address))
                if address.is_global:
                    target["non_bot_public_ips"][key].add(str(address))
    target["invalid_ip_requests"] += address is None
    target["non_public_ip_requests"] += address is not None and not address.is_global
    if bot is not None:
        target["known_bot_requests"][kind] += bot
        target["known_bot_requests"]["all"] += bot
    if client is not None:
        client_type = {"web-app": "web_app", "unmarked": "unmarked"}.get(client, "unknown")
        metrics = target["client_types"][client_type]
        metrics["requests"]["all"] += 1
        metrics["requests"][kind] += 1
        metrics["calculation_submissions"] += kind == "calculation_submission"
        if address is not None:
            metrics["ips"].add(str(address))
            if address.is_global:
                metrics["public_ips"].add(str(address))
    if status is not None:
        target["statuses"][str(status)] += 1
        target["calculation_http_2xx"] += kind == "calculation_submission" and 200 <= status < 300


def summarize(target, source):
    return {
        "requests": {k: target["requests"][k] for k in CATEGORIES},
        "status_counts": dict(sorted(target["statuses"].items())),
        "unique_ips": {k: len(v) for k, v in target["ips"].items()},
        "unique_public_ips": {k: len(v) for k, v in target["public_ips"].items()},
        "unique_non_bot_ips": {k: len(v) for k, v in target["non_bot_ips"].items()} if source == "nginx" else None,
        "unique_non_bot_public_ips": {k: len(v) for k, v in target["non_bot_public_ips"].items()} if source == "nginx" else None,
        "known_bot_requests": dict(target["known_bot_requests"]) if source == "nginx" else None,
        "non_bot_requests": {k: target["requests"][k] - target["known_bot_requests"][k]
                             for k in CATEGORIES} if source == "nginx" else None,
        "client_classification": {
            name: {"requests": {k: metrics["requests"][k] for k in ("all", "calculation_submission")},
                   "unique_ips": len(metrics["ips"]),
                   "unique_public_ips": len(metrics["public_ips"]),
                   "calculation_submissions": metrics["calculation_submissions"]}
            for name, metrics in target["client_types"].items()
        } if source == "nginx" else None,
        "non_public_ip_requests": target["non_public_ip_requests"],
        "invalid_ip_requests": target["invalid_ip_requests"],
        "calculation_http_2xx": target["calculation_http_2xx"] if source == "nginx" else None,
        "calculation_successes": None,
        "cohorts": {
            name: {"unique_ips": len(target["ips"][category] - target["ips"]["calculation_submission"]),
                   "unique_public_ips": len(target["public_ips"][category] - target["public_ips"]["calculation_submission"])}
            for name, category in COHORTS.items()
        },
    }


def collect_source(source, paths, year, start_date=None, end_date=None):
    start, end = date_bounds(year, start_date, end_date)
    annual = bucket()
    monthly = {}
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month) and datetime(y, m, 1, tzinfo=timezone.utc) < end:
        monthly[f"{y:04d}-{m:02d}"] = bucket()
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    result = {"files": [], "warnings": [], "lines": 0, "malformed_lines": 0,
              "ignored_lines": 0, "outside_year_requests": 0, "outside_period_requests": 0,
              "coverage": {"first_request_utc": None, "last_request_utc": None,
                           "first_in_year_utc": None, "last_in_year_utc": None,
                           "first_in_period_utc": None, "last_in_period_utc": None}}
    seen = set()
    for path in sorted(map(Path, paths)):
        # Do not read a supplied file twice or follow server symlinks to other data.
        if path.is_symlink():
            result["warnings"].append(f"Skipped symlink: {path}")
            continue
        try:
            stat = path.stat()
            identity = (stat.st_dev, stat.st_ino)
            if identity in seen:
                result["warnings"].append(f"Skipped duplicate file: {path}")
                continue
            seen.add(identity)
            if not path.is_file():
                raise OSError("not a regular file")
            opener = gzip.open if path.suffix == ".gz" else open
            with opener(path, "rt", encoding="utf-8", errors="replace") as handle:
                result["files"].append(str(path))
                for line in handle:
                    result["lines"] += 1
                    try:
                        event = parse(source, line)
                        if event is None:
                            result["ignored_lines"] += 1
                            continue
                        time, ip, method, url, status, bot, client = event
                        kind = category(method, url)
                    except (ValueError, KeyError, TypeError, OverflowError):
                        result["malformed_lines"] += 1
                        continue
                    iso = time.isoformat()
                    coverage = result["coverage"]
                    coverage["first_request_utc"] = min(coverage["first_request_utc"] or iso, iso)
                    coverage["last_request_utc"] = max(coverage["last_request_utc"] or iso, iso)
                    if time.year != year:
                        result["outside_year_requests"] += 1
                    else:
                        coverage["first_in_year_utc"] = min(coverage["first_in_year_utc"] or iso, iso)
                        coverage["last_in_year_utc"] = max(coverage["last_in_year_utc"] or iso, iso)
                    if not start <= time < end:
                        result["outside_period_requests"] += 1
                        continue
                    coverage["first_in_period_utc"] = min(coverage["first_in_period_utc"] or iso, iso)
                    coverage["last_in_period_utc"] = max(coverage["last_in_period_utc"] or iso, iso)
                    try:
                        address = ipaddress.ip_address(ip)
                    except ValueError:
                        address = None
                    add(annual, kind, address, status, bot, client)
                    add(monthly[f"{time.year:04d}-{time.month:02d}"], kind, address, status, bot, client)
        except (OSError, EOFError, zlib.error) as exc:
            result["warnings"].append(f"Could not completely read {path}: {exc}")
    if not result["files"]:
        result["warnings"].append(f"Missing source: no readable {source} logs")
    if not annual["requests"]["all"]:
        result["warnings"].append(f"No valid {source} requests in UTC interval [{start.isoformat()}, {end.isoformat()}); not proof of no usage")
    if result["malformed_lines"]:
        result["warnings"].append("Malformed lines excluded; counts are incomplete")
    if annual["non_public_ip_requests"]:
        result["warnings"].append("Non-public addresses excluded from public-IP counts; API client addresses may be proxies")
    if annual["invalid_ip_requests"]:
        result["warnings"].append("Invalid IP addresses excluded from unique-IP counts")
    if source == "api":
        result["warnings"].append("API timestamps have no timezone; assumed UTC. Verify the server logging timezone")
    result["annual"] = summarize(annual, source)
    result["monthly"] = {month: summarize(value, source) for month, value in monthly.items()}
    return result


def collect(nginx, api, year, start_date=None, end_date=None, database=False):
    start, end = date_bounds(year, start_date, end_date)
    return {
        "schema_version": 2, "year": year, "timezone": "UTC",
        "period": {"start_inclusive_utc": start.isoformat(), "end_exclusive_utc": end.isoformat()},
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "Full sequential scan, not an atomic snapshot or cache; rotation and overlapping copies may affect counts",
            "Sources overlap and must not be summed; only retained readable logs are covered",
            "Unique IPs are not people: NAT, proxies, dynamic addresses and bots affect counts",
            "Annual unique-IP counts are set unions, not sums of monthly counts",
            "Without-submission cohorts subtract IPs with any observed submission in the same period, including rejected requests",
            "Website documents are GETs to explicit frontend routes; assets and wildcard routes are excluded",
            "Example API requests are molecules, mmcif and example downloads, not thumbnails or distinct sessions",
            "Calculation submissions are POST requests; HTTP 2xx means HTTP acceptance, not successful calculation",
            "API response lines are ignored; HTTP acceptance and calculation success are unknown for that source",
            "Nginx bot flags are a user-agent substring heuristic; non-bot counts exclude flagged requests, not all bots",
            "API logs do not retain user agents, so bot-excluded API counts are unavailable",
            "Web-app client marker is an explicit frontend header; unmarked clients are not necessarily scripts, and old logs are unknown",
            "The annual metrics key contains the selected interval; monthly CSV counts are clipped to that interval",
            "Database aggregates cover retained calculation sets by created_at, not requests or fresh executions; methods can overlap and cache reuse is not distinguished",
            "Database dates are computation-record creation times: setup may create the record before execution, or result storage after execution; they are not reliable submission/execution times or durations",
            "Molecule counts sum distinct input hashes within each set; atom sizes deduplicate linked hashes across the interval, not chemical structures",
            "Atom sizes describe input metadata, not necessarily computed atoms after settings/filtering; multi-molecule inputs cannot resolve individual atom sizes",
            "Missing metadata is unknown, not zero; partially missing associations within otherwise populated sets cannot be detected; retention limits historical coverage",
            "Database collection reads aggregate metadata only, never charge JSON, samples or results files",
            "Actual computation durations are not stored; HTTP response times are not background-job runtimes",
        ],
        "database": collect_database(start, end) if database else {
            "status": "not_requested", "warnings": ["Database not requested; counts are unknown, not zero"]},
        "sources": {"nginx": collect_source("nginx", nginx, year, start_date, end_date),
                    "api": collect_source("api", api, year, start_date, end_date)},
    }


def remote_collect(args):
    host = args.host or SERVERS[args.server]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]*", host):
        raise ValueError("invalid SSH host")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", args.user):
        raise ValueError("invalid SSH user")
    remote_args = ["python3", "-B", "-", "--collect", "--year", str(args.year)]
    for option, value in (("--start-date", args.start_date), ("--end-date", args.end_date)):
        if value:
            remote_args.extend([option, value])
    if args.database:
        remote_args.append("--database")
    command = ["ssh", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
               "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=15", "-o",
               "ServerAliveCountMax=2", "-l", args.user, host, shlex.join(remote_args)]
    completed = subprocess.run(command, input=Path(__file__).read_text(encoding="utf-8"),
                               text=True, capture_output=True, timeout=args.ssh_timeout, check=True)
    report = json.loads(completed.stdout)
    report["collection"] = {"mode": "ssh", "host": host, "user": args.user}
    if completed.stderr.strip():
        report["collector_warning"] = completed.stderr.strip()
    return report


def text_report(report):
    period = report["period"]
    lines = [f"UTC interval: [{period['start_inclusive_utc']}, {period['end_exclusive_utc']})"]
    for source, data in report["sources"].items():
        lines.append(f"{source}: {data['annual']['requests']['all']} requests; "
                     f"{data['annual']['requests']['calculation_submission']} calculation submissions")
        if data["annual"]["non_bot_requests"] is not None:
            lines.append(f"  Known-bot-flagged calculation submissions: "
                         f"{data['annual']['known_bot_requests'].get('calculation_submission', 0)}; "
                         f"not flagged: {data['annual']['non_bot_requests']['calculation_submission']}")
        if data["annual"]["client_classification"] is not None:
            for name, client_metrics in data["annual"]["client_classification"].items():
                lines.append(f"  {name}: {client_metrics['requests']['all']} requests, "
                             f"{client_metrics['calculation_submissions']} calculation submissions, "
                             f"{client_metrics['unique_ips']} distinct IPs")
        lines.extend(f"Warning: {warning}" for warning in data["warnings"])
    db = report["database"]
    lines.append(f"Database: {db['status']}")
    lines.extend(f"Warning: {warning}" for warning in db["warnings"])
    if db["status"] == "available":
        lines.append("Database coverage (selected interval unless retained/all-time):")
        lines.extend(f"  {key}: {value if value is not None else 'unknown'}" for key, value in db["coverage"].items())
        lines.append("Methods: calculation sets per method (overlapping, not executions)")
        lines.extend(f"  {row['method']}: {row['calculation_sets']}" for row in db["methods_per_calculation_set"])
        for key, title in (("molecules_per_set", "Molecules per calculation set"),
                           ("linked_input_atom_sizes", "Atoms per molecule in distinct linked inputs")):
            lines.append(title)
            for name, value in db[key].items():
                if name != "histogram":
                    lines.append(f"  {name}: {value if value is not None else 'unknown'}")
            rows = list(db[key]["histogram"])
            if key == "linked_input_atom_sizes":
                rows.append({"bin": "unresolved multi-molecule", "count": db[key]["unresolved_multi_molecule_count"]})
            denominator = sum(row["count"] for row in rows)
            lines.append(f"  Histogram: {denominator} records including unknown bins; # approximately 2 percentage points")
            for row in rows:
                share = 100 * row["count"] / denominator if denominator else 0
                percent = f"{share:.1f}%" if denominator else "n/a"
                bar = "#" * max(1, round(share / 2)) if row["count"] else ""
                lines.append(f"    {row['bin']:<26} {row['count']:>8} {percent:>7}  {bar}")
    lines.append("Limitations:")
    lines.extend(f"- {value}" for value in report["limitations"])
    return "\n".join(lines) + "\n"


def write_report(report, output):
    output.mkdir(parents=True, exist_ok=True)
    targets = [output / "report.json", output / "report.txt", output / "monthly.csv"]
    for path in targets:
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"Refusing to overwrite {path}; choose a new output directory")
    with (output / "report.json").open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    with (output / "report.txt").open("x", encoding="utf-8") as handle:
        handle.write(text_report(report))
    with (output / "monthly.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source", "month", "category", "requests", "unique_ips", "unique_public_ips",
                         "unique_non_bot_ips", "unique_non_bot_public_ips", "non_bot_requests",
                         "calculation_http_2xx", "calculation_successes", "known_bot_requests", "status_counts",
                         "client_type", "client_calculation_submissions", "client_unique_ips",
                         "client_unique_public_ips"])
        for source, data in report["sources"].items():
            for month, metrics in data["monthly"].items():
                for kind in CATEGORIES:
                    writer.writerow([source, month, kind, metrics["requests"][kind],
                                      metrics["unique_ips"][kind], metrics["unique_public_ips"][kind],
                                      metrics["unique_non_bot_ips"][kind] if metrics["unique_non_bot_ips"] is not None else None,
                                      metrics["unique_non_bot_public_ips"][kind] if metrics["unique_non_bot_public_ips"] is not None else None,
                                      metrics["non_bot_requests"][kind] if metrics["non_bot_requests"] is not None else None,
                                      metrics["calculation_http_2xx"] if kind == "calculation_submission" else None,
                                       "unknown", metrics["known_bot_requests"].get(kind, 0) if metrics["known_bot_requests"] is not None else None,
                                        json.dumps(metrics["status_counts"], sort_keys=True) if kind == "all" else "",
                                        "", "", "", ""])
                for kind, cohort in metrics["cohorts"].items():
                    writer.writerow([source, month, kind, "", cohort["unique_ips"],
                                     cohort["unique_public_ips"], None, None, None, "", "unknown", None, "",
                                     "", "", "", ""])
                if metrics["client_classification"] is not None:
                    for client_type, client_metrics in metrics["client_classification"].items():
                        writer.writerow([source, month, "client_classification", client_metrics["requests"]["all"],
                                         client_metrics["unique_ips"], client_metrics["unique_public_ips"],
                                         None, None, None, None, "unknown", None, "", client_type,
                                         client_metrics["calculation_submissions"], client_metrics["unique_ips"],
                                         client_metrics["unique_public_ips"]])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    remote = parser.add_mutually_exclusive_group()
    remote.add_argument("--server", choices=SERVERS)
    remote.add_argument("--host")
    parser.add_argument("--user", default="ubuntu")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--start-date", help="Inclusive UTC YYYY-MM-DD (default: year start)")
    parser.add_argument("--end-date", help="Exclusive UTC YYYY-MM-DD (default: next year start)")
    parser.add_argument("--database", action="store_true", help="Opt in to read-only metadata aggregates in SSH mode")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--nginx-log", action="append", default=[], type=Path)
    parser.add_argument("--api-log", action="append", default=[], type=Path)
    parser.add_argument("--ssh-timeout", type=int, default=1800, help="Total SSH scan timeout in seconds (default: 1800)")
    parser.add_argument("--collect", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not 1 <= args.year <= 9999 or args.ssh_timeout <= 0:
        parser.error("year must be 1..9999 and SSH timeout must be positive")
    try:
        date_bounds(args.year, args.start_date, args.end_date)
    except ValueError as exc:
        parser.error(str(exc))
    offline = bool(args.nginx_log or args.api_log)
    if offline and args.database:
        parser.error("--database is only available in SSH mode, not offline log mode")
    if args.collect:
        if offline or args.host or args.server or args.output:
            parser.error("internal collector does not accept source or output options")
        report = collect(Path("/var/log/acc/nginx").glob("access.log*"),
                         [Path("/var/log/acc/logs.log")], args.year,
                         args.start_date, args.end_date, args.database)
        print(json.dumps(report))
        return 0
    if not args.output or (offline and (args.server or args.host)) or not (offline or args.server or args.host):
        parser.error("provide --output and either --server/--host or offline log paths, not both")
    try:
        if offline:
            report = collect(args.nginx_log, args.api_log, args.year,
                             args.start_date, args.end_date)
            report["collection"] = {"mode": "offline"}
        else:
            report = remote_collect(args)
        write_report(report, args.output)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"usage-stats: {exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            print(exc.stderr.strip(), file=sys.stderr)
        return 1
    print(f"Wrote {args.output / 'report.json'}, {args.output / 'report.txt'} and {args.output / 'monthly.csv'}")
    if report["database"]["status"] == "available":
        print(f"database: {report['database']['coverage']['calculation_sets']} computation records in selected interval")
    for warning in report["database"]["warnings"]:
        print(f"database: {warning}", file=sys.stderr)
    for source, data in report["sources"].items():
        metrics = data["annual"]
        print(f"{source}: {metrics['requests']['all']} requests; "
              f"{metrics['requests']['calculation_submission']} calculation submissions; "
              f"{metrics['requests']['example_api']} example-content requests; "
              f"{metrics['unique_public_ips']['website_document']} public website IPs")
        if metrics["unique_non_bot_ips"] is not None:
            print(f"{source}: {metrics['unique_non_bot_ips']['all']} distinct IPs on requests not flagged "
                  f"as bots; calculation submissions: "
                  f"{metrics['known_bot_requests'].get('calculation_submission', 0)} flagged as bots, "
                  f"{metrics['non_bot_requests']['calculation_submission']} not flagged")
        for warning in data["warnings"]:
            print(f"{source}: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
