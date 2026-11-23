# C# workbook

## Contents

- [Header](#header)
- [Load when](#load-when)
- [Overview](#overview)
- [Setup and configuration](#setup-and-configuration)
- [Idioms and patterns](#idioms-and-patterns)
- [Pitfalls](#pitfalls)
- [Commands](#commands)
- [Testing](#testing)
- [Security](#security)
- [Performance](#performance)
- [Deployment and operations](#deployment-and-operations)
- [Our situation](#our-situation)
- [Skills and agents](#skills-and-agents)

## Header

| Key | Value |
| --- | --- |
| Technology | `csharp` |
| Title | C# |
| Versions | C# 14 and 15 (.NET 10 and 11) |
| Supported until | 2028-11-14 |
| Version command | `dotnet --version` |
| Layer | base |
| Updated | 2026-11-23 |

Sources:

- [The history of C#](https://learn.microsoft.com/dotnet/csharp/whats-new/csharp-version-history) · checked 2026-11-20
- [Configure C# language version](https://learn.microsoft.com/dotnet/csharp/language-reference/configure-language-version) · checked 2026-11-20
- [C# documentation, Microsoft Learn](https://learn.microsoft.com/dotnet/csharp/) · checked 2026-11-18
- [Nullable reference types](https://learn.microsoft.com/dotnet/csharp/nullable-references) · checked 2026-11-18
- [Asynchronous programming with async and await](https://learn.microsoft.com/dotnet/csharp/asynchronous-programming/) · checked 2026-11-18
- [Async return types (C#)](https://learn.microsoft.com/dotnet/csharp/asynchronous-programming/async-return-types) · checked 2026-11-18
- [C# coding conventions](https://learn.microsoft.com/dotnet/csharp/fundamentals/coding-style/coding-conventions) · checked 2026-11-18
- [Implement a DisposeAsync method](https://learn.microsoft.com/dotnet/standard/garbage-collection/implementing-disposeasync) · checked 2026-11-18
- [Pattern matching overview](https://learn.microsoft.com/dotnet/csharp/fundamentals/functional/pattern-matching) · checked 2026-11-18
- [C# record types](https://learn.microsoft.com/dotnet/csharp/fundamentals/types/records) · checked 2026-11-18
- [Best practices for exceptions](https://learn.microsoft.com/dotnet/standard/exceptions/best-practices-for-exceptions) · checked 2026-11-23
- [Overview of .NET source code analysis](https://learn.microsoft.com/dotnet/fundamentals/code-analysis/overview) · checked 2026-11-18
- [Best practices for comparing strings in .NET](https://learn.microsoft.com/dotnet/standard/base-types/best-practices-strings) · checked 2026-11-18
- [dotnet format](https://learn.microsoft.com/dotnet/core/tools/dotnet-format) · checked 2026-11-18
- [Introduction to LINQ queries](https://learn.microsoft.com/dotnet/csharp/linq/get-started/introduction-to-linq-queries) · checked 2026-11-18
- [dotnet/skills](https://github.com/dotnet/skills) · checked 2026-11-18 · MIT, secondary source
- [Checked and unchecked statements](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/statements/checked-and-unchecked) · checked 2026-11-22
- [Arithmetic operators (C# reference)](https://learn.microsoft.com/dotnet/csharp/language-reference/operators/arithmetic-operators) · checked 2026-11-23
- [Math.Round method](https://learn.microsoft.com/dotnet/api/system.math.round) · checked 2026-11-23

## Load when

| Glob |
| --- |
| `**/*.cs` |
| `**/*.csx` |

## Overview

- **csharp.overview.001** · C# is a statically typed, object-oriented language that also supports functional-style features such as pattern matching, records, and LINQ. This workbook covers the language; the .NET platform has its own workbook. · tags: style · source: [C# documentation, Microsoft Learn](https://learn.microsoft.com/dotnet/csharp/) · confirmed: base, 2026-11-18
- **csharp.overview.002** · Nullable reference types are a compile-time feature only: runtime behavior does not change, and the compiler reports warnings when code and annotations disagree. · tags: async · source: [Nullable reference types](https://learn.microsoft.com/dotnet/csharp/nullable-references) · confirmed: base, 2026-11-18
- **csharp.overview.003** · `async` and `await` compile to a generated state machine. A method that awaits a task is suspended without blocking its thread and resumes when the task completes. · tags: data · source: [Asynchronous programming with async and await](https://learn.microsoft.com/dotnet/csharp/asynchronous-programming/) · confirmed: base, 2026-11-18
- **csharp.overview.004** · Records add compiler-generated value equality, a formatted `ToString`, and `with` expressions to a class or struct; the underlying type still decides reference or value semantics. · tags: dependencies · source: [C# record types](https://learn.microsoft.com/dotnet/csharp/fundamentals/types/records) · confirmed: base, 2026-11-18
- **csharp.overview.005** · The .NET team publishes agent skills for .NET and C# in the `dotnet/skills` repository, which is a secondary reference for agent guidance. · tags: versions · source: [dotnet/skills](https://github.com/dotnet/skills) · confirmed: base, 2026-11-18
- **csharp.overview.006** · C# 14 was released in November 2025 and C# 15 in November 2026, alongside .NET 10 and .NET 11. · tags: versions, build · source: [The history of C#](https://learn.microsoft.com/dotnet/csharp/whats-new/csharp-version-history) · confirmed: base, 2026-11-20
- **csharp.overview.007** · The default C# language version follows the project's target framework; setting `LangVersion` to `latest` makes the build depend on the installed compiler. · tags: versions, build · source: [Configure C# language version](https://learn.microsoft.com/dotnet/csharp/language-reference/configure-language-version) · confirmed: base, 2026-11-20

## Setup and configuration

- **csharp.setup.001** · Set `<Nullable>enable</Nullable>` in the project file; templates set it for new projects, but older projects may lack it. · tags: nullability, config · source: [Nullable reference types](https://learn.microsoft.com/dotnet/csharp/nullable-references) · confirmed: base, 2026-11-18
- **csharp.setup.002** · Code-quality rules (prefix `CA`) are on by default for projects that target .NET 5 or later, but the default mode turns only a few rules into build warnings. Choose a stricter mode with `AnalysisMode` when more is wanted. · tags: linting, build · source: [Overview of .NET source code analysis](https://learn.microsoft.com/dotnet/fundamentals/code-analysis/overview) · confirmed: base, 2026-11-18
- **csharp.setup.003** · Code-style rules (prefix `IDE`) are not enforced in command-line builds unless `EnforceCodeStyleInBuild` is `true`. · tags: style, linting, build · source: [Overview of .NET source code analysis](https://learn.microsoft.com/dotnet/fundamentals/code-analysis/overview) · confirmed: base, 2026-11-18
- **csharp.setup.004** · Set rule severity in `.editorconfig`, for example `dotnet_diagnostic.CA1822.severity = none`; `AnalysisLevel` set to `latest` follows the SDK, while a fixed value such as `8.0` pins the rule set. · tags: linting, config · source: [Overview of .NET source code analysis](https://learn.microsoft.com/dotnet/fundamentals/code-analysis/overview) · confirmed: base, 2026-11-18
- **csharp.setup.005** · Enforce coding conventions with an `.editorconfig` plus analyzers so violations show up in every build. · tags: style, linting · source: [C# coding conventions](https://learn.microsoft.com/dotnet/csharp/fundamentals/coding-style/coding-conventions) · confirmed: base, 2026-11-18
- **csharp.setup.006** · The `-warnaserror` flag also turns `CA` warnings into errors; set `CodeAnalysisTreatWarningsAsErrors` to `false` to prevent that. · tags: linting, build · source: [Overview of .NET source code analysis](https://learn.microsoft.com/dotnet/fundamentals/code-analysis/overview) · confirmed: base, 2026-11-18

## Idioms and patterns

- **csharp.patterns.001** · MUST · Annotate intent with `string` versus `string?` and fix null warnings by checking, restructuring, or annotating the API instead of silencing them. · tags: nullability · source: [Nullable reference types](https://learn.microsoft.com/dotnet/csharp/nullable-references) · confirmed: base, 2026-11-18
- **csharp.patterns.002** · SHOULD · Describe null contracts on your own APIs with nullable analysis attributes such as `[NotNullWhen(true)]` rather than using the null-forgiving operator at each call site. · tags: nullability · source: [Nullable reference types](https://learn.microsoft.com/dotnet/csharp/nullable-references) · confirmed: base, 2026-11-18
- **csharp.patterns.003** · SHOULD · Test for null with `is null` and `is not null`; these patterns do not call a user-defined `==` or `!=`. · tags: nullability · source: [Pattern matching overview](https://learn.microsoft.com/dotnet/csharp/fundamentals/functional/pattern-matching) · confirmed: base, 2026-11-18
- **csharp.patterns.004** · MUST · Use `await using` for `IAsyncDisposable` resources. · tags: lifecycle, async · source: [Implement a DisposeAsync method](https://learn.microsoft.com/dotnet/standard/garbage-collection/implementing-disposeasync) · confirmed: base, 2026-11-18
- **csharp.patterns.005** · SHOULD · Use `using` statements or declarations in place of a `try-finally` whose only job is to call `Dispose`. · tags: lifecycle · source: [C# coding conventions](https://learn.microsoft.com/dotnet/csharp/fundamentals/coding-style/coding-conventions) · confirmed: base, 2026-11-18
- **csharp.patterns.006** · SHOULD · Use records for data-holding types whose instances with equal values should be equal; prefer `record class` for large or inherited types and `record struct` for small values. · tags: data · source: [C# record types](https://learn.microsoft.com/dotnet/csharp/fundamentals/types/records) · confirmed: base, 2026-11-18
- **csharp.patterns.007** · SHOULD · Throw argument errors with the static helpers such as `ArgumentNullException.ThrowIfNull`, `ArgumentOutOfRangeException.ThrowIfNegative` and `ThrowIfGreaterThan` (.NET 8 and later), and `ObjectDisposedException.ThrowIf`, and use predefined exception types like `InvalidOperationException` for wrong state. · tags: errors · source: [Best practices for exceptions](https://learn.microsoft.com/dotnet/standard/exceptions/best-practices-for-exceptions) · confirmed: base, 2026-11-23
- **csharp.patterns.008** · SHOULD · Use file-scoped namespaces, collection expressions (`[1, 2, 3]`), and `required` properties in new code instead of older equivalents. · tags: style · source: [C# coding conventions](https://learn.microsoft.com/dotnet/csharp/fundamentals/coding-style/coding-conventions) · confirmed: base, 2026-11-18

## Pitfalls

- **csharp.pitfalls.001** · MUST NOT · Do not block a thread waiting on a task, such as `Task.Delay(3000).Wait()`; use `await`, which suspends the method without blocking its thread. · tags: async · source: [Asynchronous programming with async and await](https://learn.microsoft.com/dotnet/csharp/asynchronous-programming/) · confirmed: base, 2026-11-18
- **csharp.pitfalls.002** · MUST NOT · Do not write `async void` except for event handlers that require it; a void async method cannot be awaited and its callers cannot catch its exceptions, which can crash the app. Return `Task` instead. · tags: async, errors · source: [Async return types (C#)](https://learn.microsoft.com/dotnet/csharp/asynchronous-programming/async-return-types) · confirmed: base, 2026-11-18
- **csharp.pitfalls.003** · SHOULD · To run async work concurrently, start the tasks first and await them later with `Task.WhenAll`. Awaiting each call immediately runs the steps one after another. · tags: async, performance · source: [Asynchronous programming with async and await](https://learn.microsoft.com/dotnet/csharp/asynchronous-programming/) · confirmed: base, 2026-11-18
- **csharp.pitfalls.004** · MUST NOT · Do not suppress nullable warnings with `!` as a habit; each use removes the compiler's protection at that spot. Spot it by counting `!.` in a diff. · tags: nullability · source: [Nullable reference types](https://learn.microsoft.com/dotnet/csharp/nullable-references) · confirmed: base, 2026-11-18
- **csharp.pitfalls.005** · MUST NOT · Do not catch `System.Exception` without an exception filter, and catch only what the code can handle; order catch clauses from most derived to least derived. · tags: errors · source: [Best practices for exceptions](https://learn.microsoft.com/dotnet/standard/exceptions/best-practices-for-exceptions) · confirmed: base, 2026-11-18
- **csharp.pitfalls.006** · MUST NOT · Do not write `throw e;` to rethrow, since it resets the stack trace; use a bare `throw;`. Analyzer CA2200 flags this. · tags: errors, logging · source: [Best practices for exceptions](https://learn.microsoft.com/dotnet/standard/exceptions/best-practices-for-exceptions) · confirmed: base, 2026-11-18
- **csharp.pitfalls.007** · MUST NOT · Do not enumerate a deferred LINQ query more than once: each enumeration re-reads the source and can give different results. Materialize with `ToList` or `ToArray` when the result is reused. · tags: data, performance · source: [Introduction to LINQ queries](https://learn.microsoft.com/dotnet/csharp/linq/get-started/introduction-to-linq-queries) · confirmed: base, 2026-11-18
- **csharp.pitfalls.008** · SHOULD · Pass an explicit `StringComparison` to string methods. `StartsWith(string)`, `IndexOf(string)`, `Compare`, and `ToUpper` are culture-sensitive by default, while `==`, `Equals`, and `Contains` are ordinal. · tags: strings · source: [Best practices for comparing strings in .NET](https://learn.microsoft.com/dotnet/standard/base-types/best-practices-strings) · confirmed: base, 2026-11-18
- **csharp.pitfalls.009** · SHOULD · Widen to `long` or bound the input before multiplying caller-supplied integers, and test at the type's limits. Non-constant integer arithmetic is unchecked by default and wraps silently. · tags: data, errors · source: [Checked and unchecked statements](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/statements/checked-and-unchecked) · confirmed: base, 2026-11-22
- **csharp.pitfalls.010** · SHOULD · Dividing two integers gives an integer rounded toward zero, so `percent / 100` is 0 for every percent below 100. Make one operand `decimal` or `double` when the result needs a fraction, for example `percent / 100m`. · tags: data · source: [Arithmetic operators (C# reference)](https://learn.microsoft.com/dotnet/csharp/language-reference/operators/arithmetic-operators) · confirmed: base, 2026-11-23
- **csharp.pitfalls.011** · SHOULD · `Math.Round` rounds a midpoint to the nearest even number by default, so `Math.Round(2.5m)` is 2. Pass `MidpointRounding.AwayFromZero` when amounts must round half away from zero, and test a midpoint value. · tags: data · source: [Math.Round method](https://learn.microsoft.com/dotnet/api/system.math.round) · confirmed: base, 2026-11-23

## Commands

- **csharp.commands.001** · `dotnet format` formats a project or solution to the `.editorconfig` settings; pass a `.sln` or `.csproj` to target it. · tags: formatting, cli · source: [dotnet format](https://learn.microsoft.com/dotnet/core/tools/dotnet-format) · confirmed: base, 2026-11-18
- **csharp.commands.002** · `dotnet format --verify-no-changes` changes nothing and exits non-zero when files would be reformatted, which suits a check step. · tags: formatting, build, cli · source: [dotnet format](https://learn.microsoft.com/dotnet/core/tools/dotnet-format) · confirmed: base, 2026-11-18
- **csharp.commands.003** · `dotnet format whitespace`, `dotnet format style`, and `dotnet format analyzers` run only that category of rules; `--diagnostics <IDs>` limits the fix to listed rule IDs and `--severity info|warn|error` sets the minimum severity (default `warn`). · tags: formatting, linting, cli · source: [dotnet format](https://learn.microsoft.com/dotnet/core/tools/dotnet-format) · confirmed: base, 2026-11-18
- **csharp.commands.004** · `dotnet format --include <paths> --exclude <paths>` limits formatting to chosen folders or files, and `--no-restore` skips the implicit restore. · tags: formatting, cli · source: [dotnet format](https://learn.microsoft.com/dotnet/core/tools/dotnet-format) · confirmed: base, 2026-11-18
- **csharp.commands.005** · MUST · `dotnet format` may restore, compile, and run analyzers from the project, so run it only on trusted code. · tags: formatting, build, access · source: [dotnet format](https://learn.microsoft.com/dotnet/core/tools/dotnet-format) · confirmed: base, 2026-11-18

## Testing

- none yet

## Security

- **csharp.security.001** · MUST · Compare identifiers, paths, protocol names, and security-relevant strings with `StringComparison.Ordinal` or `OrdinalIgnoreCase`, never a culture-sensitive comparison. · tags: strings, access · source: [Best practices for comparing strings in .NET](https://learn.microsoft.com/dotnet/standard/base-types/best-practices-strings) · confirmed: base, 2026-11-18
- **csharp.security.002** · MUST NOT · Do not use culture-sensitive case-insensitive checks such as `StartsWith("FILE:", true, null)` for validation; on Turkish locales they can be bypassed. · tags: strings, access · source: [Best practices for comparing strings in .NET](https://learn.microsoft.com/dotnet/standard/base-types/best-practices-strings) · confirmed: base, 2026-11-18
- **csharp.security.003** · SHOULD · Normalize case with `ToUpperInvariant`, not `ToLowerInvariant`; `OrdinalIgnoreCase` is the preferred way to compare ignoring case. · tags: strings, access · source: [Best practices for comparing strings in .NET](https://learn.microsoft.com/dotnet/standard/base-types/best-practices-strings) · confirmed: base, 2026-11-18
- **csharp.security.004** · SHOULD · Turn on analyzers CA1307, CA1309, and CA1310 to flag unintended linguistic comparisons. · tags: linting, strings · source: [Best practices for comparing strings in .NET](https://learn.microsoft.com/dotnet/standard/base-types/best-practices-strings) · confirmed: base, 2026-11-18
- **csharp.security.005** · MUST NOT · Do not throw from `Equals`, `GetHashCode`, `ToString`, static constructors, or `finally` blocks, and do not throw the reserved types `NullReferenceException` or `IndexOutOfRangeException`. · tags: errors · source: [Best practices for exceptions](https://learn.microsoft.com/dotnet/standard/exceptions/best-practices-for-exceptions) · confirmed: base, 2026-11-18

## Performance

- **csharp.performance.001** · Ordinal string comparison is the fastest and does not depend on the thread's culture. · tags: strings · source: [Best practices for comparing strings in .NET](https://learn.microsoft.com/dotnet/standard/base-types/best-practices-strings) · confirmed: base, 2026-11-18
- **csharp.performance.002** · Use `StringBuilder` when appending in loops, and interpolation for short strings. · tags: strings · source: [C# coding conventions](https://learn.microsoft.com/dotnet/csharp/fundamentals/coding-style/coding-conventions) · confirmed: base, 2026-11-18
- **csharp.performance.003** · Prefer `TryParse` and `TryGetValue` over catching exceptions where failure is routine, since exceptions are costly. · tags: errors · source: [Best practices for exceptions](https://learn.microsoft.com/dotnet/standard/exceptions/best-practices-for-exceptions) · confirmed: base, 2026-11-18
- **csharp.performance.004** · In .NET 8 and later, `SearchValues<T>` is a reusable optimized set lookup; create it once and cache it. · tags: strings · source: [Best practices for comparing strings in .NET](https://learn.microsoft.com/dotnet/standard/base-types/best-practices-strings) · confirmed: base, 2026-11-18
- **csharp.performance.005** · Sorting and grouping operators (`OrderBy`, `GroupBy`, `Reverse`) read the whole source before yielding, while `Where` and `Select` stream element by element. · tags: data · source: [Introduction to LINQ queries](https://learn.microsoft.com/dotnet/csharp/linq/get-started/introduction-to-linq-queries) · confirmed: base, 2026-11-18
- **csharp.performance.006** · `record struct` equality is generated without reflection, so it is faster than the default equality of a plain struct. · tags: data · source: [C# record types](https://learn.microsoft.com/dotnet/csharp/fundamentals/types/records) · confirmed: base, 2026-11-18

## Deployment and operations

- none yet

## Our situation

- none yet

## Skills and agents

- `dev-workbook` - keeps this workbook; the dev skills read it through `workbook.py resolve`.
