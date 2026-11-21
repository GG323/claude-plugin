"""Create, remove, and sweep throwaway test containers, labelled with the run ID. Standard library only.

Usage:
  py -3 -I ephemeral.py up --run-id <id> --name <name> --image <image[:tag]> --port <container port>
                           [--env KEY=VALUE ...] [--dry-run]
  py -3 -I ephemeral.py down --run-id <id> [--dry-run]
  py -3 -I ephemeral.py sweep [--older-than-hours 6] [--dry-run]

up     Starts one detached container named <run id>-<name>, labelled howtoai.dev=1 and
       howtoai.dev.run=<run id>, with the port published on 127.0.0.1 only (a random host port),
       and prints the host and port to use. The image must name a tag; "latest" is refused, so
       a rerun gets the same image. Environment values must be test-only (no secrets: the
       container is reachable only from this machine; use images that allow passwordless local
       access, for example POSTGRES_HOST_AUTH_METHOD=trust).
down   Removes every container (and its anonymous volumes) labelled with the run ID.
sweep  Removes containers labelled howtoai.dev=1 that were created more than N hours ago
       (orphans of runs that did not tear down).
--dry-run prints the docker commands without running them, and works without Docker. Without
Docker, down and sweep return ok with "docker_missing": true and remove nothing (no container can
exist); up fails.

Prints one JSON object: {"ok", "commands", ...}.
"""

import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys

LABEL = "howtoai.dev"
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}$")
SECRETISH = re.compile(r"(password|secret|token|key)", re.I)


class Fail(Exception):
    pass


def out(obj, code=0):
    print(json.dumps(obj, ensure_ascii=False, indent=1))
    sys.exit(code)


def docker():
    exe = shutil.which("docker")
    if not exe:
        raise Fail("docker not found; install Docker or set testing.ephemeral to none, then ask the user for a target")
    return exe


def no_docker(commands):
    """down and sweep without Docker: no container can exist, so there is nothing to remove."""
    return {"ok": True, "dry_run": False, "docker_missing": True, "removed": [], "commands": commands}


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if p.returncode != 0:
        raise Fail(f"{' '.join(cmd[:3])} ... failed: {p.stderr.strip()[:300]}")
    return p.stdout.strip()


def up(a):
    if not RUN_ID.match(a.run_id) or not RUN_ID.match(a.name):
        raise Fail("run id and name may hold letters, digits, '.', '_', and '-' only")
    if ":" not in a.image.rsplit("/", 1)[-1] or a.image.endswith(":latest"):
        raise Fail("pin the image to a tag other than latest, for example postgres:17-alpine")
    envs = []
    for e in a.env or []:
        if "=" not in e:
            raise Fail(f"--env needs KEY=VALUE, got {e!r}")
        k, v = e.split("=", 1)
        if SECRETISH.search(k) and v and v.lower() not in ("trust", "true", "yes", "1"):
            raise Fail(f"{k} looks like a secret; use passwordless local access instead")
        envs += ["-e", e]
    cname = f"{a.run_id}-{a.name}"
    start = ["docker", "run", "-d", "--name", cname, "--label", f"{LABEL}=1", "--label", f"{LABEL}.run={a.run_id}",
             "-p", f"127.0.0.1::{a.port}", *envs, a.image]
    port_cmd = ["docker", "port", cname, f"{a.port}/tcp"]
    if a.dry_run:
        return {"ok": True, "dry_run": True, "name": cname, "label": f"{LABEL}.run={a.run_id}",
                "commands": [" ".join(start), " ".join(port_cmd)], "host": "127.0.0.1", "port": None}
    exe = docker()
    start[0] = port_cmd[0] = exe
    cid = run(start)
    mapped = run(port_cmd).splitlines()[0]
    host, port = mapped.rsplit(":", 1)
    return {"ok": True, "dry_run": False, "name": cname, "id": cid[:12], "label": f"{LABEL}.run={a.run_id}",
            "host": host, "port": int(port), "commands": [" ".join(start[1:]), " ".join(port_cmd[1:])]}


def down(a):
    if not RUN_ID.match(a.run_id):
        raise Fail("bad run id")
    ls = ["docker", "ps", "-aq", "--filter", f"label={LABEL}.run={a.run_id}"]
    if a.dry_run:
        return {"ok": True, "dry_run": True, "commands": [" ".join(ls), "docker rm -f -v <each id>"], "removed": []}
    if not shutil.which("docker"):
        return no_docker([" ".join(ls)])
    exe = docker()
    ls[0] = exe
    ids = run(ls).split()
    if ids:
        run([exe, "rm", "-f", "-v", *ids])
    return {"ok": True, "dry_run": False, "removed": ids, "commands": [" ".join(ls[1:])]}


def sweep(a):
    ls = ["docker", "ps", "-a", "--filter", f"label={LABEL}=1", "--format", "{{.ID}} {{.CreatedAt}}"]
    if a.dry_run:
        return {"ok": True, "dry_run": True, "commands": [" ".join(ls), "docker rm -f -v <ids older than the cutoff>"],
                "removed": []}
    if not shutil.which("docker"):
        return no_docker([" ".join(ls)])
    exe = docker()
    ls[0] = exe
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=a.older_than_hours)
    old = []
    for line in run(ls).splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            created = datetime.datetime.strptime(" ".join(parts[1:4]), "%Y-%m-%d %H:%M:%S %z")
        except ValueError:
            continue
        if created < cutoff:
            old.append(parts[0])
    if old:
        run([exe, "rm", "-f", "-v", *old])
    return {"ok": True, "dry_run": False, "removed": old, "commands": [" ".join(ls[1:])]}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Throwaway test containers.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("up")
    u.add_argument("--run-id", required=True)
    u.add_argument("--name", required=True)
    u.add_argument("--image", required=True)
    u.add_argument("--port", required=True, type=int)
    u.add_argument("--env", action="append")
    u.add_argument("--dry-run", action="store_true")
    d = sub.add_parser("down")
    d.add_argument("--run-id", required=True)
    d.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("sweep")
    s.add_argument("--older-than-hours", type=float, default=6)
    s.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    try:
        out({"up": up, "down": down, "sweep": sweep}[a.cmd](a))
    except (Fail, subprocess.TimeoutExpired) as e:
        out({"ok": False, "error": str(e)}, 1)


if __name__ == "__main__":
    main()
