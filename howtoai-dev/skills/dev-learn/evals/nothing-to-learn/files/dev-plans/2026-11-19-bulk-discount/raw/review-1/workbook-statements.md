## C# (C# 12 and 13 (.NET 8 and 9))
### Idioms and patterns
- csharp.patterns.001 MUST: Annotate intent with `string` versus `string?` and fix null warnings by checking, restructuring, or annotating the API instead of silencing them.
- csharp.patterns.002 SHOULD: Describe null contracts on your own APIs with nullable analysis attributes such as `[NotNullWhen(true)]` rather than using the null-forgiving operator at each call site.
- csharp.patterns.003 SHOULD: Test for null with `is null` and `is not null`; these patterns do not call a user-defined `==` or `!=`.
- csharp.patterns.004 MUST: Use `await using` for `IAsyncDisposable` resources.
- csharp.patterns.005 SHOULD: Use `using` statements or declarations in place of a `try-finally` whose only job is to call `Dispose`.
- csharp.patterns.006 SHOULD: Use records for data-holding types whose instances with equal values should be equal; prefer `record class` for large or inherited types and `record struct` for small values.
- csharp.patterns.007 SHOULD: Throw argument errors with the static helpers such as `ArgumentNullException.ThrowIfNull` and `ObjectDisposedException.ThrowIf`, and use predefined exception types like `InvalidOperationException` for wrong state.
- csharp.patterns.008 SHOULD: Use file-scoped namespaces, collection expressions (`[1, 2, 3]`), and `required` properties in new code instead of older equivalents.
### Pitfalls
- csharp.pitfalls.001 MUST NOT: Do not block a thread waiting on a task, such as `Task.Delay(3000).Wait()`; use `await`, which suspends the method without blocking its thread.
- csharp.pitfalls.002 MUST NOT: Do not write `async void` except for event handlers that require it; a void async method cannot be awaited and its callers cannot catch its exceptions, which can crash the app. Return `Task` instead.
- csharp.pitfalls.003 SHOULD: To run async work concurrently, start the tasks first and await them later with `Task.WhenAll`. Awaiting each call immediately runs the steps one after another.
- csharp.pitfalls.004 MUST NOT: Do not suppress nullable warnings with `!` as a habit; each use removes the compiler's protection at that spot. Spot it by counting `!.` in a diff.
- csharp.pitfalls.005 MUST NOT: Do not catch `System.Exception` without an exception filter, and catch only what the code can handle; order catch clauses from most derived to least derived.
- csharp.pitfalls.006 MUST NOT: Do not write `throw e;` to rethrow, since it resets the stack trace; use a bare `throw;`. Analyzer CA2200 flags this.
- csharp.pitfalls.007 MUST NOT: Do not enumerate a deferred LINQ query more than once: each enumeration re-reads the source and can give different results. Materialize with `ToList` or `ToArray` when the result is reused.
- csharp.pitfalls.008 SHOULD: Pass an explicit `StringComparison` to string methods. `StartsWith(string)`, `IndexOf(string)`, `Compare`, and `ToUpper` are culture-sensitive by default, while `==`, `Equals`, and `Contains` are ordinal.
### Security
- csharp.security.001 MUST: Compare identifiers, paths, protocol names, and security-relevant strings with `StringComparison.Ordinal` or `OrdinalIgnoreCase`, never a culture-sensitive comparison.
- csharp.security.002 MUST NOT: Do not use culture-sensitive case-insensitive checks such as `StartsWith("FILE:", true, null)` for validation; on Turkish locales they can be bypassed.
- csharp.security.003 SHOULD: Normalize case with `ToUpperInvariant`, not `ToLowerInvariant`; `OrdinalIgnoreCase` is the preferred way to compare ignoring case.
- csharp.security.004 SHOULD: Turn on analyzers CA1307, CA1309, and CA1310 to flag unintended linguistic comparisons.
- csharp.security.005 MUST NOT: Do not throw from `Equals`, `GetHashCode`, `ToString`, static constructors, or `finally` blocks, and do not throw the reserved types `NullReferenceException` or `IndexOutOfRangeException`.
### Performance
- csharp.performance.001: Ordinal string comparison is the fastest and does not depend on the thread's culture.
- csharp.performance.002: Use `StringBuilder` when appending in loops, and interpolation for short strings.
- csharp.performance.003: Prefer `TryParse` and `TryGetValue` over catching exceptions where failure is routine, since exceptions are costly.
- csharp.performance.004: In .NET 8 and later, `SearchValues<T>` is a reusable optimized set lookup; create it once and cache it.
- csharp.performance.005: Sorting and grouping operators (`OrderBy`, `GroupBy`, `Reverse`) read the whole source before yielding, while `Where` and `Select` stream element by element.
- csharp.performance.006: `record struct` equality is generated without reflection, so it is faster than the default equality of a plain struct.
## .NET (.NET 8 (LTS) and .NET 9)
### Idioms and patterns
- dotnet.patterns.001 MUST: Obtain `HttpClient` through `IHttpClientFactory` (`AddHttpClient`, named or typed clients), not by creating one per request.
- dotnet.patterns.002 SHOULD: Bind configuration to strongly typed options classes with `Configure<T>(GetSection(...))` and validate them with `ValidateDataAnnotations()` plus `ValidateOnStart()` so bad settings fail at startup.
- dotnet.patterns.003 SHOULD: Pick the options interface by lifetime: `IOptions<T>` for fixed values, `IOptionsSnapshot<T>` for per-request values in scoped services, `IOptionsMonitor<T>` for singletons that must see changes.
- dotnet.patterns.004 SHOULD: Inject `ILogger<T>` from the container, pass exceptions as the first argument of the log call, and use message templates (or `[LoggerMessage]`) instead of string interpolation.
- dotnet.patterns.005 MUST NOT: Call `BuildServiceProvider` while configuring services; use the registration overloads that receive an `IServiceProvider` instead.
- dotnet.patterns.006 SHOULD: Keep exception handling first in the middleware order, with `UseCors` before authentication and `UseAuthentication` before `UseAuthorization`.
- dotnet.patterns.007 SHOULD: Register health checks with `AddHealthChecks()` and expose them with `MapHealthChecks`, using tags and `Predicate` to separate liveness from readiness.
### Pitfalls
- dotnet.pitfalls.001: Secrets placed in `appsettings.json` or other checked-in files end up in source control; spot them as connection strings with passwords or API keys in `appsettings*.json`.
- dotnet.pitfalls.002: `new HttpClient()` per request, or a typed client captured in a singleton, can exhaust sockets or keep stale DNS; spot it as `new HttpClient` inside methods or singleton constructors.
- dotnet.pitfalls.003: A singleton that takes a scoped service holds it beyond its lifetime (captive dependency); `validateScopes: true` makes the container throw, and a scoped service resolved outside a scope behaves as a singleton.
- dotnet.pitfalls.004: `IOptionsSnapshot<T>` cannot be injected into a singleton and `IOptions<T>` never reloads; picking the wrong one shows up as an injection error or as settings that never change.
- dotnet.pitfalls.005: Without `TreatWarningsAsErrors` the build keeps producing output despite warnings, so nullable and analyzer warnings pile up unnoticed.
- dotnet.pitfalls.006: MSBuild uses only the first `Directory.Build.props` found searching upward from the project, so a nested one hides the root file's settings unless it imports the parent.
- dotnet.pitfalls.007: A `Version` attribute left on a `PackageReference` under central package management, or several package sources without source mapping, produces restore errors or warning `NU1507`.
### Testing
- dotnet.testing.001: The filter properties differ by framework: MSTest has `TestCategory`, `Priority`, `ClassName`, and `Name`; NUnit has `Category` and `Property`; xUnit has `DisplayName` and `Traits`.
- dotnet.testing.002: An MSTest `ClassName` filter needs the full namespace-qualified class name; the short class name matches nothing.
- dotnet.testing.003: With the .NET 10 SDK and later, `dotnet test` can use Microsoft.Testing.Platform through a `test.runner` entry in `global.json`; VSTest stays the default, and MTP-only options such as `--treenode-filter` fail under VSTest.
- dotnet.testing.004: ASP.NET Core integration tests use `WebApplicationFactory<TEntryPoint>` from `Microsoft.AspNetCore.Mvc.Testing`; keep them in a project separate from unit tests and do not reference `TestServer` packages directly.
- dotnet.testing.005: In integration tests, replace services with `ConfigureTestServices` inside `WithWebHostBuilder`; the app's own `DbContext` registration must be removed first, and SQLite in-memory is preferred over the EF in-memory provider.
- dotnet.testing.006: The test client follows redirects by default; set `AllowAutoRedirect = false` to assert a 302 and its `Location` header, and note that POST requests need an antiforgery cookie and token.
### Security
- dotnet.security.001 MUST NOT: Store secrets in `appsettings.json` or any checked-in file; use `dotnet user-secrets` for development and a controlled store such as Azure Key Vault or the environment for production.
- dotnet.security.002 MUST NOT: Treat Secret Manager as encrypted or as a production store; it keeps plain JSON in the user profile and is for development only.
- dotnet.security.003 MUST NOT: Use production secrets in development or test.
- dotnet.security.004 SHOULD: Treat files under `wwwroot` as public, because `UseStaticFiles` performs no authorization.
- dotnet.security.005 SHOULD: Add `RequireAuthorization` to health check endpoints that expose detail, because `RequireHost` matches the spoofable `Host` header.
- dotnet.security.006 SHOULD: Run `dotnet format` only on trusted code, because it may restore, compile, and run analyzers from the project.
### Performance
- dotnet.performance.001: The factory caches one handler per client name with a default lifetime of 2 minutes, so handlers are reused across `CreateClient` calls; disposing a client does not dispose its handler.
- dotnet.performance.002: `[LoggerMessage]` source generation is preferred over plain log extension calls for performance, and logger methods are synchronous, so queue slow log sinks to a background worker.
- dotnet.performance.003: Keep DI factories fast and synchronous; resolving async work with `.Result` can deadlock, and `async` service resolution is not supported.
- dotnet.performance.004: Health checks run on every request to the endpoint, so keep them cheap (a connection check, or `SELECT 1`) and use a publisher for scheduled runs.
