#!/usr/bin/env python3
"""
fake_logs.py — generate realistic-looking log files for testing.

Generates a mix of:
- system logs (sshd, sudo, kernel-ish messages)
- web/server logs (Nginx/Apache combined style)
- application logs (structured-ish app messages)
- database logs (PostgreSQL/MySQL-ish messages)

Examples:
  python3 fake_logs.py --out fake.log --lines 5000 --profile mixed
  python3 fake_logs.py --out app.log --lines 2000 --profile app
  python3 fake_logs.py --out server.log --lines 3000 --profile server
  python3 fake_logs.py --out db.log --lines 1500 --profile db --error-rate 0.08
"""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, List, Tuple


# -----------------------------
# Utilities
# -----------------------------
def rand_choice(rng: random.Random, items: List[str]) -> str:
    return items[rng.randrange(len(items))]


def rand_ip(rng: random.Random) -> str:
    # avoid 0/255 extremes for nicer-looking IPs
    return ".".join(str(rng.randint(1, 254)) for _ in range(4))


def rand_uuid_like(rng: random.Random) -> str:
    # lightweight UUID-ish
    hexchars = "0123456789abcdef"
    parts = [
        "".join(rng.choice(hexchars) for _ in range(8)),
        "".join(rng.choice(hexchars) for _ in range(4)),
        "".join(rng.choice(hexchars) for _ in range(4)),
        "".join(rng.choice(hexchars) for _ in range(4)),
        "".join(rng.choice(hexchars) for _ in range(12)),
    ]
    return "-".join(parts)


def iso_ts(dt: datetime) -> str:
    # e.g. 2026-02-12T20:15:03.123-05:00
    return dt.isoformat(timespec="milliseconds")


def sys_ts(dt: datetime) -> str:
    # e.g. Feb 12 20:15:03
    return dt.strftime("%b %d %H:%M:%S")


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


# -----------------------------
# Profiles
# -----------------------------
@dataclass
class Context:
    rng: random.Random
    host: str
    tz: timezone
    app_name: str
    env: str
    service: str


def gen_system_line(ctx: Context, dt: datetime, is_error: bool) -> str:
    rng = ctx.rng
    host = ctx.host
    user = rand_choice(rng, ["neel", "ubuntu", "ec2-user", "deploy", "postgres", "root", "admin"])
    src_ip = rand_ip(rng)
    pid = rng.randint(100, 99999)

    # Bias toward "ERROR" patterns for your bash grep tests
    if is_error:
        templates = [
            f"{sys_ts(dt)} {host} sshd[{pid}]: ERROR Failed password for invalid user {user} from {src_ip} port {rng.randint(1024,65535)} ssh2",
            f"{sys_ts(dt)} {host} sudo[{pid}]: ERROR pam_unix(sudo:auth): authentication failure; logname={user} uid={rng.randint(0,1000)} euid=0 tty=/dev/pts/{rng.randint(0,9)} ruser={user} rhost= user={user}",
            f"{sys_ts(dt)} {host} kernel: ERROR Out of memory: Kill process {pid} ({rand_choice(rng,['python','node','java','nginx'])}) score {rng.randint(100,1000)} or sacrifice child",
            f"{sys_ts(dt)} {host} systemd[{rng.randint(1,500)}]: ERROR Failed to start {rand_choice(rng,['docker','nginx','postgresql','ssh'])}.service: Unit entered failed state.",
        ]
    else:
        templates = [
            f"{sys_ts(dt)} {host} sshd[{pid}]: Accepted publickey for {user} from {src_ip} port {rng.randint(1024,65535)} ssh2",
            f"{sys_ts(dt)} {host} sudo[{pid}]: {user} : TTY=pts/{rng.randint(0,9)} ; PWD=/home/{user} ; USER=root ; COMMAND=/usr/bin/{rand_choice(rng,['apt','systemctl','journalctl','tail'])}",
            f"{sys_ts(dt)} {host} systemd[{rng.randint(1,500)}]: Started {rand_choice(rng,['Daily apt download activities','Session 42 of User','Cleanup of Temporary Directories'])}.",
            f"{sys_ts(dt)} {host} cron[{pid}]: ({user}) CMD ({rand_choice(rng,['/usr/local/bin/backup','/usr/local/bin/rotate_logs','/usr/bin/python3 /opt/app/job.py'])})",
        ]
    return rand_choice(rng, templates)


def gen_server_line(ctx: Context, dt: datetime, is_error: bool) -> str:
    rng = ctx.rng
    ip = rand_ip(rng)
    method = rand_choice(rng, ["GET", "POST", "PUT", "DELETE"])
    path = rand_choice(
        rng,
        ["/", "/login", "/logout", "/api/v1/users", "/api/v1/orders", "/health", "/metrics", "/static/app.js", "/admin"],
    )
    proto = "HTTP/1.1"
    ua = rand_choice(
        rng,
        [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0 Safari/537.36",
            "curl/8.4.0",
            "PostmanRuntime/7.36.0",
        ],
    )
    referer = rand_choice(rng, ["-", "https://example.com/", "https://app.example.com/dashboard"])
    bytes_sent = rng.randint(200, 50000)
    req_id = rand_uuid_like(rng)

    # Nginx/Apache combined log style, plus a request id at end
    if is_error:
        status = rand_choice(rng, ["500", "502", "503", "504", "429"])
        # include "ERROR" keyword for easy matching
        return (
            f'{ip} - - [{dt.strftime("%d/%b/%Y:%H:%M:%S %z")}] "{method} {path} {proto}" {status} {bytes_sent} '
            f'"{referer}" "{ua}" req_id={req_id} ERROR upstream_failure'
        )
    else:
        status = rand_choice(rng, ["200", "201", "204", "301", "302", "304", "400", "401", "403", "404"])
        # keep non-error most of the time
        if status in {"500", "502", "503", "504"}:
            status = "200"
        return (
            f'{ip} - - [{dt.strftime("%d/%b/%Y:%H:%M:%S %z")}] "{method} {path} {proto}" {status} {bytes_sent} '
            f'"{referer}" "{ua}" req_id={req_id}'
        )


def gen_app_line(ctx: Context, dt: datetime, is_error: bool) -> str:
    rng = ctx.rng
    level = "ERROR" if is_error else rand_choice(rng, ["INFO", "DEBUG", "WARN"])
    thread = rand_choice(rng, ["main", "worker-1", "worker-2", "http-nio-8080-exec-1", "scheduler"])
    component = rand_choice(rng, ["auth", "payments", "orders", "users", "cache", "api", "db"])
    req_id = rand_uuid_like(rng)
    user_id = rng.randint(1000, 9999)

    if is_error:
        msgs = [
            f"ERROR Invalid credentials for user_id={user_id}",
            f"ERROR Timeout while calling upstream service=inventory",
            f"ERROR Failed to connect to database host=db01 port=5432",
            f"ERROR Unhandled exception: NullPointerException at {component}.py:{rng.randint(10,400)}",
            f"ERROR Rate limit exceeded for user_id={user_id}",
        ]
    else:
        msgs = [
            f"User login successful user_id={user_id}",
            f"Cache hit key=session:{user_id}",
            f"Request completed status=200 duration_ms={rng.randint(5,450)}",
            f"Background job executed job=refresh_metrics duration_ms={rng.randint(50,2000)}",
            f"Created order order_id={rng.randint(100000,999999)} amount={rng.randint(10,500)} currency=CAD",
        ]

    msg = rand_choice(rng, msgs)
    # structured-ish log line
    return (
        f"{iso_ts(dt)} level={level} app={ctx.app_name} env={ctx.env} service={ctx.service} "
        f"thread={thread} component={component} req_id={req_id} msg=\"{msg}\""
    )


def gen_db_line(ctx: Context, dt: datetime, is_error: bool) -> str:
    rng = ctx.rng
    db = rand_choice(rng, ["appdb", "users", "orders", "analytics"])
    user = rand_choice(rng, ["app", "readonly", "admin", "etl"])
    pid = rng.randint(100, 99999)
    duration_ms = rng.randint(1, 2500)

    if is_error:
        msgs = [
            f"ERROR:  relation \"{rand_choice(rng,['users','orders','payments'])}\" does not exist",
            "ERROR:  deadlock detected",
            "ERROR:  could not serialize access due to concurrent update",
            "ERROR:  remaining connection slots are reserved for non-replication superuser connections",
            "ERROR:  canceling statement due to statement timeout",
        ]
        detail = rand_choice(rng, msgs)
        return (
            f"{iso_ts(dt)} db=postgres pid={pid} user={user} database={db} ERROR {detail} "
            f"query_id={rand_uuid_like(rng)}"
        )
    else:
        statement = rand_choice(
            rng,
            [
                "SELECT * FROM users WHERE id=$1",
                "UPDATE orders SET status=$1 WHERE id=$2",
                "INSERT INTO payments(order_id, amount) VALUES($1,$2)",
                "DELETE FROM sessions WHERE expires_at < NOW()",
                "SELECT COUNT(*) FROM events WHERE created_at > NOW() - interval '1 day'",
            ],
        )
        return (
            f"{iso_ts(dt)} db=postgres pid={pid} user={user} database={db} "
            f"LOG duration={duration_ms}ms statement={statement} query_id={rand_uuid_like(rng)}"
        )


# -----------------------------
# Main generator
# -----------------------------
def build_generators(profile: str) -> List[Tuple[str, Callable[[Context, datetime, bool], str]]]:
    gens = {
        "system": [("system", gen_system_line)],
        "server": [("server", gen_server_line)],
        "app": [("app", gen_app_line)],
        "db": [("db", gen_db_line)],
        "mixed": [
            ("system", gen_system_line),
            ("server", gen_server_line),
            ("app", gen_app_line),
            ("db", gen_db_line),
        ],
    }
    if profile not in gens:
        raise ValueError(f"Unknown profile '{profile}'. Choose from: {', '.join(gens.keys())}")
    return gens[profile]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate fake logs for testing.")
    parser.add_argument("--out", required=True, help="Output log file path")
    parser.add_argument("--lines", type=int, default=1000, help="Number of log lines to generate")
    parser.add_argument(
        "--profile",
        choices=["system", "server", "app", "db", "mixed"],
        default="mixed",
        help="Log profile/type",
    )
    parser.add_argument("--error-rate", type=float, default=0.05, help="Fraction of lines that should be errors (0..1)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible logs")
    parser.add_argument("--host", default="ip-10-0-1-23", help="Hostname to use in system logs")
    parser.add_argument("--app", dest="app_name", default="payments-api", help="App name used in app logs")
    parser.add_argument("--env", default="prod", help="Environment label used in app logs")
    parser.add_argument("--service", default="api", help="Service label used in app logs")
    parser.add_argument(
        "--start-minutes-ago",
        type=int,
        default=60,
        help="Start timestamp minutes in the past (default 60)",
    )
    parser.add_argument(
        "--jitter-ms",
        type=int,
        default=900,
        help="Random jitter added per line in milliseconds (default 900)",
    )

    args = parser.parse_args()

    rng = random.Random(args.seed)
    error_rate = clamp01(args.error_rate)

    # Use America/Toronto offset similar to your environment (-05:00); keep it fixed for simplicity
    tz = timezone(timedelta(hours=-5))

    now = datetime.now(tz=tz)
    dt = now - timedelta(minutes=max(0, args.start_minutes_ago))

    ctx = Context(
        rng=rng,
        host=args.host,
        tz=tz,
        app_name=args.app_name,
        env=args.env,
        service=args.service,
    )

    generators = build_generators(args.profile)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as f:
        for _ in range(args.lines):
            # Choose which generator to use (weighted a bit toward app/server in mixed)
            if args.profile == "mixed":
                pick = rng.random()
                if pick < 0.20:
                    gen = gen_system_line
                elif pick < 0.55:
                    gen = gen_server_line
                elif pick < 0.85:
                    gen = gen_app_line
                else:
                    gen = gen_db_line
            else:
                gen = generators[0][1]

            is_error = rng.random() < error_rate

            line = gen(ctx, dt, is_error)
            f.write(line + "\n")

            # Advance time by a small randomized delta
            dt += timedelta(milliseconds=rng.randint(10, max(10, args.jitter_ms)))

    print(f"Wrote {args.lines} lines to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
