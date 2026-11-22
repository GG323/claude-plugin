"""Grade a task flow's code, independent of what the skills reported.

Usage: py -3 -I -B check_task.py <flow> <workspace>

Copies the repository to a temporary folder, adds a test the skills never saw,
and runs it there. The workspace is never written to. Exit code 0 is a pass,
1 is a fail, and 2 is a check that could not run.
"""

import json
import shutil
import subprocess
import sys
import tempfile
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

CHECKS = {
    "F3": {
        "repository": "shop",
        "project": "tests/Api.Tests",
        "test": F3_TEST,
        "filter": "FullyQualifiedName~Shop.SystemCheck",
    },
}


def check(flow, workspace):
    spec = CHECKS[flow]
    with tempfile.TemporaryDirectory(prefix=f"dev-check-{flow}-") as temp:
        copy = Path(temp) / spec["repository"]
        shutil.copytree(
            workspace / spec["repository"],
            copy,
            ignore=shutil.ignore_patterns(".git", "bin", "obj", "TestResults", ".env.production"),
        )
        (copy / spec["project"] / "SystemCheck.cs").write_text(spec["test"], encoding="utf-8")
        run = subprocess.run(
            ["dotnet", "test", spec["project"], "--filter", spec["filter"], "-nodeReuse:false"],
            cwd=copy,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )

    lines = run.stdout.splitlines()
    summary = next((line.strip() for line in lines if "Failed:" in line and "Passed:" in line), None)
    if summary is None:
        return 2, {"flow": flow, "result": "blocked", "output": lines[-15:]}
    result = "pass" if run.returncode == 0 else "fail"
    return run.returncode and 1, {"flow": flow, "result": result, "summary": summary}


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in CHECKS:
        raise SystemExit(__doc__)
    code, report = check(sys.argv[1], Path(sys.argv[2]).resolve())
    print(json.dumps(report, indent=1))
    raise SystemExit(code)
