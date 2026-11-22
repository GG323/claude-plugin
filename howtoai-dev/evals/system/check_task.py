"""Grade a task flow's code, independent of what the skills reported.

Usage: py -3 -I -B check_task.py <flow> <workspace> [--baseline]

Copies the repository to a temporary folder, adds a test the skills never saw,
runs it, then starts the app there and checks it over HTTP, because a unit
test that builds its own objects cannot see broken wiring. The workspace is
never written to.

--baseline proves a fresh bed: it passes only when the planted bug is there
and everything around it works. Exit code 0 is a pass, 1 is a fail, and 2 is
a check that could not run.
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

F3_TEST = """using Shop.Api.Orders;
using Xunit;

namespace Shop.SystemCheck;

public class F3Check
{
    [Theory]
    [InlineData(1, 10, 1, 10)]
    [InlineData(2, 10, 11, 10)]
    [InlineData(3, 10, 21, 5)]
    [InlineData(1, 1, 1, 1)]
    [InlineData(25, 1, 25, 1)]
    [InlineData(1, 100, 1, 25)]
    public void Page_starts_at_the_right_order(int page, int size, int firstId, int count)
    {
        var result = new OrderQueries(new OrderStore()).List(page, size);

        Assert.Equal(Enumerable.Range(firstId, count), result.Items.Select(order => order.Id));
    }

    [Theory]
    [InlineData(10, 3)]
    [InlineData(25, 1)]
    [InlineData(100, 1)]
    public void Page_count_is_unchanged(int size, int pages)
    {
        Assert.Equal(pages, new OrderQueries(new OrderStore()).List(1, size).TotalPages);
    }
}
"""

# (path, status, IDs when fixed, IDs on the fresh bed, total pages)
F3_HTTP = [
    ("/orders", 200, list(range(1, 11)), list(range(11, 21)), 3),
    ("/orders?page=2&size=10", 200, list(range(11, 21)), list(range(21, 26)), 3),
    ("/orders?page=3&size=10", 200, list(range(21, 26)), [], 3),
    ("/orders?page=0", 400, None, None, None),
    ("/orders?size=0", 400, None, None, None),
    ("/orders?size=101", 400, None, None, None),
]

CHECKS = {
    "F3": {
        "repository": "shop",
        "project": "tests/Api.Tests",
        "test": F3_TEST,
        "filter": "FullyQualifiedName~Shop.SystemCheck",
        "baseline_failures": 6,
        "app": "src/Api",
        "assembly": "Api.dll",
        "http": F3_HTTP,
    },
}


def dotnet(cwd, *args):
    return subprocess.run(
        ["dotnet", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def get(url):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url, timeout=10) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        return error.code, {}


def check_http(spec, copy, baseline):
    """Return the mismatches, or None when the app could not be started."""
    app = copy / spec["app"]
    if dotnet(app, "build", "-o", "out", "-nodeReuse:false").returncode:
        return None
    base = f"http://127.0.0.1:{free_port()}"
    process = subprocess.Popen(
        ["dotnet", str(app / "out" / spec["assembly"]), "--urls", base],
        cwd=app,
        env=dict(os.environ, ASPNETCORE_ENVIRONMENT="Local", DOTNET_ENVIRONMENT="Local"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 60
        while True:
            try:
                get(base + "/health")
                break
            except OSError:
                if process.poll() is not None or time.monotonic() > deadline:
                    return None
                time.sleep(0.3)

        problems = []
        for path, status, fixed, broken, pages in spec["http"]:
            got_status, body = get(base + path)
            if got_status != status:
                problems.append(f"{path}: status {got_status}, expected {status}")
            elif status == 200:
                ids = [order["id"] for order in body.get("items", [])]
                expected = broken if baseline else fixed
                if ids != expected or body.get("totalPages") != pages:
                    problems.append(f"{path}: IDs {ids}, totalPages {body.get('totalPages')}; expected {expected}, {pages}")
        return problems
    finally:
        process.kill()
        process.wait(timeout=20)


def check(flow, workspace, baseline):
    spec = CHECKS[flow]
    with tempfile.TemporaryDirectory(prefix=f"dev-check-{flow}-", ignore_cleanup_errors=True) as temp:
        copy = Path(temp) / spec["repository"]
        shutil.copytree(
            workspace / spec["repository"],
            copy,
            ignore=shutil.ignore_patterns(".git", "bin", "obj", "out", "TestResults", ".env.production"),
        )
        http = check_http(spec, copy, baseline)
        if http is None:
            return 2, {"flow": flow, "result": "blocked", "output": "the app did not build or start"}

        (copy / spec["project"] / "SystemCheck.cs").write_text(spec["test"], encoding="utf-8")
        run = dotnet(copy, "test", spec["project"], "--filter", spec["filter"], "-nodeReuse:false")

    lines = run.stdout.splitlines()
    summary = next((line.strip() for line in lines if "Failed:" in line and "Passed:" in line), None)
    if summary is None:
        return 2, {"flow": flow, "result": "blocked", "output": lines[-15:]}

    failed = int(summary.split("Failed:")[1].split(",")[0])
    tests_ok = failed == spec["baseline_failures"] if baseline else run.returncode == 0
    passed = tests_ok and not http
    report = {
        "flow": flow,
        "mode": "baseline" if baseline else "outcome",
        "result": "pass" if passed else "fail",
        "tests": summary,
        "http": http or "as expected",
    }
    return (0 if passed else 1), report


if __name__ == "__main__":
    args = [arg for arg in sys.argv[1:] if arg != "--baseline"]
    if len(args) != 2 or args[0] not in CHECKS:
        raise SystemExit(__doc__)
    code, report = check(args[0], Path(args[1]).resolve(), "--baseline" in sys.argv)
    print(json.dumps(report, indent=1))
    raise SystemExit(code)
