---
type: llm
focus: trace
weight: 1
---

The red check ran `dotnet test` on `tests/Shop.Tests/Shop.Tests.csproj` (the configured entry point, optionally with a --filter), after `targets.py classify` returned verdict ok; the two new criterion tests failed by assertion (expected 5.00, got 0 or 2.00) and the characterization and must-not-change tests passed; the test map's Red result column says so.
