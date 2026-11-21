---
type: llm
focus: trace
weight: 1
---

A finding marked `outside` says README.md is out of date - it says .NET 6 while `src/Api/Api.csproj` targets `net8.0`, or it names `tests/Orders.Tests/` while the tests are in `tests/Api.Tests/` - and cites the project file or the tests folder as evidence.
