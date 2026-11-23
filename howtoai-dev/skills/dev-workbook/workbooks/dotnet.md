# .NET workbook

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
| Technology | `dotnet` |
| Title | .NET |
| Versions | .NET 10 (LTS) and .NET 11 (STS) |
| Supported until | 2028-11-14 |
| Version command | `dotnet --version` |
| Layer | base |
| Updated | 2026-11-22 |

Sources:

- [.NET and .NET Core Support Policy](https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core) · checked 2026-11-20
- [global.json overview](https://learn.microsoft.com/en-us/dotnet/core/tools/global-json) · checked 2026-11-18
- [Central Package Management](https://learn.microsoft.com/en-us/nuget/consume-packages/central-package-management) · checked 2026-11-18
- [HttpClientFactory in .NET](https://learn.microsoft.com/en-us/dotnet/core/extensions/httpclient-factory) · checked 2026-11-18
- [Safe storage of app secrets in development](https://learn.microsoft.com/en-us/aspnet/core/security/app-secrets) · checked 2026-11-18
- [Run selected unit tests](https://learn.microsoft.com/en-us/dotnet/core/testing/selective-unit-tests) · checked 2026-11-22
- [Containerize a .NET app with dotnet publish](https://learn.microsoft.com/en-us/dotnet/core/containers/sdk-publish) · checked 2026-11-18
- [Dependency injection guidelines](https://learn.microsoft.com/en-us/dotnet/core/extensions/dependency-injection/guidelines) · checked 2026-11-18
- [Health checks in ASP.NET Core](https://learn.microsoft.com/en-us/aspnet/core/host-and-deploy/health-checks) · checked 2026-11-18
- [Customize your build by folder](https://learn.microsoft.com/en-us/visualstudio/msbuild/customize-by-directory) · checked 2026-11-18
- [Integration tests in ASP.NET Core](https://learn.microsoft.com/en-us/aspnet/core/test/integration-tests) · checked 2026-11-18
- [Options pattern in .NET](https://learn.microsoft.com/en-us/dotnet/core/extensions/options) · checked 2026-11-18
- [dotnet format](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-format) · checked 2026-11-18
- [dotnet test](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-test) · checked 2026-11-22
- [ASP.NET Core middleware](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/middleware/) · checked 2026-11-18
- [Logging in .NET](https://learn.microsoft.com/en-us/dotnet/core/extensions/logging) · checked 2026-11-18
- [C# compiler options for errors and warnings](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/compiler-options/errors-warnings) · checked 2026-11-18
- [Configuration in ASP.NET Core](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/configuration/) · checked 2026-11-22
- [xunit on NuGet](https://www.nuget.org/packages/xunit) · checked 2026-11-22
- [SmtpClient class](https://learn.microsoft.com/en-us/dotnet/api/system.net.mail.smtpclient) · checked 2026-11-22
- [EnableSsl property](https://learn.microsoft.com/en-us/dotnet/api/system.net.mail.smtpclient.enablessl) · checked 2026-11-22
- [Containerize a .NET app reference](https://learn.microsoft.com/en-us/dotnet/core/containers/publish-configuration) · checked 2026-11-22

## Load when

| Glob |
| --- |
| `**/*.csproj` |
| `**/*.sln` |
| `**/*.slnx` |
| `**/Directory.Build.props` |
| `**/Directory.Packages.props` |
| `**/global.json` |
| `**/appsettings*.json` |
| `**/nuget.config` |

## Overview

- **dotnet.overview.001** · The `dotnet` CLI drives the SDK: restore, build, test, publish, format, and user secrets all run through it, and the SDK version is chosen independently of the runtime version a project targets. · tags: cli, build · source: [global.json overview](https://learn.microsoft.com/en-us/dotnet/core/tools/global-json) · confirmed: base, 2026-11-18
- **dotnet.overview.002** · Without a `global.json`, the highest installed SDK is used, so builds can differ between machines and CI. · tags: versions, build · source: [global.json overview](https://learn.microsoft.com/en-us/dotnet/core/tools/global-json) · confirmed: base, 2026-11-18
- **dotnet.overview.003** · ASP.NET Core requests flow through an ordered middleware pipeline, and each component decides whether to call the next one or short-circuit. · tags: http, lifecycle · source: [ASP.NET Core middleware](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/middleware/) · confirmed: base, 2026-11-18
- **dotnet.overview.004** · Configuration, options, logging, and dependency injection come from the generic host, shared by web apps, worker services, and console apps built on `Microsoft.Extensions.*`. · tags: config, di, logging · source: [Options pattern in .NET](https://learn.microsoft.com/en-us/dotnet/core/extensions/options) · confirmed: base, 2026-11-18
- **dotnet.overview.005** · Supported releases are .NET 10 (LTS) and .NET 11 (STS), both until 2028-11-14; .NET 8 and .NET 9 reached end of support on 2026-11-10. Even-numbered releases are LTS with three years of support and odd-numbered releases are STS with two. · tags: versions · source: [.NET and .NET Core Support Policy](https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core) · confirmed: base, 2026-11-20

## Setup and configuration

- **dotnet.setup.001** · Pin the SDK with a `global.json` that has a full version (no `10`, `8.0`, or wildcards) and a `rollForward` policy such as `latestFeature`. · tags: versions, build · source: [global.json overview](https://learn.microsoft.com/en-us/dotnet/core/tools/global-json) · confirmed: base, 2026-11-18
- **dotnet.setup.002** · Create it with `dotnet new globaljson --sdk-version <version> --roll-forward latestFeature`; the default policy with a version set is `patch`. · tags: versions, cli · source: [global.json overview](https://learn.microsoft.com/en-us/dotnet/core/tools/global-json) · confirmed: base, 2026-11-18
- **dotnet.setup.003** · Put shared project properties (nullable, warnings, language settings) in a `Directory.Build.props` at the repository root; MSBuild stops at the first such file found going upward. · tags: config, build · source: [Customize your build by folder](https://learn.microsoft.com/en-us/visualstudio/msbuild/customize-by-directory) · confirmed: base, 2026-11-18
- **dotnet.setup.004** · A nested `Directory.Build.props` must import its parent with `GetPathOfFileAbove`, or the parent's settings are silently skipped; the file name is case-sensitive on Linux. · tags: config, build · source: [Customize your build by folder](https://learn.microsoft.com/en-us/visualstudio/msbuild/customize-by-directory) · confirmed: base, 2026-11-18
- **dotnet.setup.005** · Enable central package management with a root `Directory.Packages.props` that sets `ManagePackageVersionsCentrally` to `true` and lists `PackageVersion` items; project `PackageReference` items then carry no `Version`. · tags: dependencies, versions · source: [Central Package Management](https://learn.microsoft.com/en-us/nuget/consume-packages/central-package-management) · confirmed: base, 2026-11-18
- **dotnet.setup.006** · Set `TreatWarningsAsErrors` (or a targeted `WarningsAsErrors`, which accepts the value `nullable`) and `Nullable` in the shared props so every project fails on new warnings. · tags: linting, nullability, build · source: [C# compiler options for errors and warnings](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/compiler-options/errors-warnings) · confirmed: base, 2026-11-18
- **dotnet.setup.007** · Read configuration in layers: `appsettings.json`, then `appsettings.{Environment}.json`, user secrets in Development, environment variables, and command-line arguments, where later sources override earlier ones and `__` stands for the hierarchy separator. `WebApplication.CreateBuilder` takes the environment from `DOTNET_ENVIRONMENT` ahead of `ASPNETCORE_ENVIRONMENT`. · tags: config, secrets · source: [Configuration in ASP.NET Core](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/configuration/) · confirmed: base, 2026-11-22

## Idioms and patterns

- **dotnet.patterns.001** · MUST · Obtain `HttpClient` through `IHttpClientFactory` (`AddHttpClient`, named or typed clients), not by creating one per request. · tags: http, di, lifecycle · source: [HttpClientFactory in .NET](https://learn.microsoft.com/en-us/dotnet/core/extensions/httpclient-factory) · confirmed: base, 2026-11-18
- **dotnet.patterns.002** · SHOULD · Bind configuration to strongly typed options classes with `Configure<T>(GetSection(...))` and validate them with `ValidateDataAnnotations()` plus `ValidateOnStart()` so bad settings fail at startup. · tags: config, errors · source: [Options pattern in .NET](https://learn.microsoft.com/en-us/dotnet/core/extensions/options) · confirmed: base, 2026-11-18
- **dotnet.patterns.003** · SHOULD · Pick the options interface by lifetime: `IOptions<T>` for fixed values, `IOptionsSnapshot<T>` for per-request values in scoped services, `IOptionsMonitor<T>` for singletons that must see changes. · tags: config, di, lifecycle · source: [Options pattern in .NET](https://learn.microsoft.com/en-us/dotnet/core/extensions/options) · confirmed: base, 2026-11-18
- **dotnet.patterns.004** · SHOULD · Inject `ILogger<T>` from the container, pass exceptions as the first argument of the log call, and use message templates (or `[LoggerMessage]`) instead of string interpolation. · tags: logging, di, errors · source: [Logging in .NET](https://learn.microsoft.com/en-us/dotnet/core/extensions/logging) · confirmed: base, 2026-11-18
- **dotnet.patterns.005** · MUST NOT · Call `BuildServiceProvider` while configuring services; use the registration overloads that receive an `IServiceProvider` instead. · tags: di · source: [Dependency injection guidelines](https://learn.microsoft.com/en-us/dotnet/core/extensions/dependency-injection/guidelines) · confirmed: base, 2026-11-18
- **dotnet.patterns.006** · SHOULD · Keep exception handling first in the middleware order, with `UseCors` before authentication and `UseAuthentication` before `UseAuthorization`. · tags: http, errors, access · source: [ASP.NET Core middleware](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/middleware/) · confirmed: base, 2026-11-18
- **dotnet.patterns.007** · SHOULD · Register health checks with `AddHealthChecks()` and expose them with `MapHealthChecks`, using tags and `Predicate` to separate liveness from readiness. · tags: health · source: [Health checks in ASP.NET Core](https://learn.microsoft.com/en-us/aspnet/core/host-and-deploy/health-checks) · confirmed: base, 2026-11-18
- **dotnet.patterns.008** · An out-of-support .NET version gets no more patches or security fixes, so a codebase on one needs an upgrade at some point. · tags: versions · source: [.NET and .NET Core Support Policy](https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core) · confirmed: base, 2026-11-20

## Pitfalls

- **dotnet.pitfalls.001** · Secrets placed in `appsettings.json` or other checked-in files end up in source control; spot them as connection strings with passwords or API keys in `appsettings*.json`. · tags: secrets, config · source: [Safe storage of app secrets in development](https://learn.microsoft.com/en-us/aspnet/core/security/app-secrets) · confirmed: base, 2026-11-18
- **dotnet.pitfalls.002** · `new HttpClient()` per request, or a typed client captured in a singleton, can exhaust sockets or keep stale DNS; spot it as `new HttpClient` inside methods or singleton constructors. · tags: http, lifecycle · source: [HttpClientFactory in .NET](https://learn.microsoft.com/en-us/dotnet/core/extensions/httpclient-factory) · confirmed: base, 2026-11-18
- **dotnet.pitfalls.003** · A singleton that takes a scoped service holds it beyond its lifetime (captive dependency); `validateScopes: true` makes the container throw, and a scoped service resolved outside a scope behaves as a singleton. · tags: di, lifecycle · source: [Dependency injection guidelines](https://learn.microsoft.com/en-us/dotnet/core/extensions/dependency-injection/guidelines) · confirmed: base, 2026-11-18
- **dotnet.pitfalls.004** · `IOptionsSnapshot<T>` cannot be injected into a singleton and `IOptions<T>` never reloads; picking the wrong one shows up as an injection error or as settings that never change. · tags: di, config, lifecycle · source: [Options pattern in .NET](https://learn.microsoft.com/en-us/dotnet/core/extensions/options) · confirmed: base, 2026-11-18
- **dotnet.pitfalls.005** · Without `TreatWarningsAsErrors` the build keeps producing output despite warnings, so nullable and analyzer warnings pile up unnoticed. · tags: linting, build, nullability · source: [C# compiler options for errors and warnings](https://learn.microsoft.com/en-us/dotnet/csharp/language-reference/compiler-options/errors-warnings) · confirmed: base, 2026-11-18
- **dotnet.pitfalls.006** · MSBuild uses only the first `Directory.Build.props` found searching upward from the project, so a nested one hides the root file's settings unless it imports the parent. · tags: config, build · source: [Customize your build by folder](https://learn.microsoft.com/en-us/visualstudio/msbuild/customize-by-directory) · confirmed: base, 2026-11-18
- **dotnet.pitfalls.007** · A `Version` attribute left on a `PackageReference` under central package management, or several package sources without source mapping, produces restore errors or warning `NU1507`. · tags: dependencies, build · source: [Central Package Management](https://learn.microsoft.com/en-us/nuget/consume-packages/central-package-management) · confirmed: base, 2026-11-18
- **dotnet.pitfalls.008** · SHOULD · Use a maintained mail library such as MailKit for new code instead of `System.Net.Mail.SmtpClient`, which is not recommended for new development. Where it stays, set `EnableSsl`, which is false by default, outside local runs. · tags: access, dependencies, config · source: [SmtpClient class](https://learn.microsoft.com/en-us/dotnet/api/system.net.mail.smtpclient), [EnableSsl property](https://learn.microsoft.com/en-us/dotnet/api/system.net.mail.smtpclient.enablessl) · confirmed: base, 2026-11-22

## Commands

- **dotnet.commands.001** · Restore, build, and test the solution with `dotnet restore`, `dotnet build --no-restore -c Release`, and `dotnet test --no-build -c Release`. · tags: build, tests, cli · source: [dotnet test](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-test) · confirmed: base, 2026-11-18
- **dotnet.commands.002** · Check formatting without changing files with `dotnet format --verify-no-changes`, which exits non-zero when files would change; `--severity` takes `info`, `warn`, or `error`. · tags: formatting, cli, build · source: [dotnet format](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-format) · confirmed: base, 2026-11-18
- **dotnet.commands.003** · Narrow `dotnet format` with the `whitespace`, `style`, or `analyzers` subcommands and `--include` and `--exclude` paths. · tags: formatting, cli · source: [dotnet format](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-format) · confirmed: base, 2026-11-18
- **dotnet.commands.004** · Filter tests with `dotnet test --filter "<Property><Operator><Value>"`, using `=`, `!=`, `~`, `!~`, with `&` and `|` and parentheses; an expression with no operator means a contains match on `FullyQualifiedName`. · tags: tests, cli · source: [Run selected unit tests](https://learn.microsoft.com/en-us/dotnet/core/testing/selective-unit-tests) · confirmed: base, 2026-11-18
- **dotnet.commands.005** · Quote the whole `--filter` value in PowerShell and whenever it contains `<`, `>`, `,`, or `|`; escape `!` as `\!` in some Linux or macOS shells and generic commas as `%2C`. · tags: tests, cli · source: [Run selected unit tests](https://learn.microsoft.com/en-us/dotnet/core/testing/selective-unit-tests) · confirmed: base, 2026-11-18
- **dotnet.commands.006** · Manage user secrets with `dotnet user-secrets init`, `set "Section:Key" "value"`, `list`, `remove`, and `clear`, adding `--project <dir>` when not in the project folder. · tags: secrets, cli · source: [Safe storage of app secrets in development](https://learn.microsoft.com/en-us/aspnet/core/security/app-secrets) · confirmed: base, 2026-11-18
- **dotnet.commands.007** · Publish a container image without a Dockerfile with `dotnet publish --os linux --arch x64 /t:PublishContainer`, optionally adding `-p ContainerRegistry=<host>` or `-p ContainerArchiveOutputPath=<file>`. · tags: image, build, cli · source: [Containerize a .NET app with dotnet publish](https://learn.microsoft.com/en-us/dotnet/core/containers/sdk-publish) · confirmed: base, 2026-11-18

## Testing

- **dotnet.testing.001** · The filter properties differ by framework: MSTest has `TestCategory`, `Priority`, `ClassName`, `Name`, and `Id` (MSTest.TestAdapter 3.6 or later); NUnit has `Category`, `TestCategory`, `Priority`, `Name`, and `Property`; xUnit has `DisplayName` and `Traits`. · tags: tests, cli · source: [Run selected unit tests](https://learn.microsoft.com/en-us/dotnet/core/testing/selective-unit-tests) · confirmed: base, 2026-11-22
- **dotnet.testing.002** · An MSTest `ClassName` filter needs the full namespace-qualified class name; the short class name matches nothing. · tags: tests · source: [Run selected unit tests](https://learn.microsoft.com/en-us/dotnet/core/testing/selective-unit-tests) · confirmed: base, 2026-11-18
- **dotnet.testing.003** · With the .NET 10 SDK and later, `dotnet test` can use Microsoft.Testing.Platform through a `test.runner` entry in `global.json`, which `DOTNET_TEST_RUNNER` overrides from .NET 11; VSTest stays the default, and MTP-only options such as `--treenode-filter` fail under VSTest. · tags: tests, versions · source: [dotnet test](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-test) · confirmed: base, 2026-11-22
- **dotnet.testing.004** · ASP.NET Core integration tests use `WebApplicationFactory<TEntryPoint>` from `Microsoft.AspNetCore.Mvc.Testing`; keep them in a project separate from unit tests and do not reference `TestServer` packages directly. · tags: tests, http · source: [Integration tests in ASP.NET Core](https://learn.microsoft.com/en-us/aspnet/core/test/integration-tests) · confirmed: base, 2026-11-18
- **dotnet.testing.005** · In integration tests, replace services with `ConfigureTestServices` inside `WithWebHostBuilder`; the app's own `DbContext` registration must be removed first, and SQLite in-memory is preferred over the EF in-memory provider. · tags: tests, data, di · source: [Integration tests in ASP.NET Core](https://learn.microsoft.com/en-us/aspnet/core/test/integration-tests) · confirmed: base, 2026-11-18
- **dotnet.testing.006** · The test client follows redirects by default; set `AllowAutoRedirect = false` to assert a 302 and its `Location` header, and note that POST requests need an antiforgery cookie and token. · tags: tests, http, access · source: [Integration tests in ASP.NET Core](https://learn.microsoft.com/en-us/aspnet/core/test/integration-tests) · confirmed: base, 2026-11-18
- **dotnet.testing.007** · The `xunit` v2 package is deprecated and gets security fixes only; `xunit.v3` replaces it and is the package for new test projects. · tags: tests, dependencies, versions · source: [xunit on NuGet](https://www.nuget.org/packages/xunit) · confirmed: base, 2026-11-22

## Security

- **dotnet.security.001** · MUST NOT · Store secrets in `appsettings.json` or any checked-in file; use `dotnet user-secrets` for development and a controlled store such as Azure Key Vault or the environment for production. · tags: secrets, config · source: [Safe storage of app secrets in development](https://learn.microsoft.com/en-us/aspnet/core/security/app-secrets) · confirmed: base, 2026-11-18
- **dotnet.security.002** · MUST NOT · Treat Secret Manager as encrypted or as a production store; it keeps plain JSON in the user profile and is for development only. · tags: secrets, config · source: [Safe storage of app secrets in development](https://learn.microsoft.com/en-us/aspnet/core/security/app-secrets) · confirmed: base, 2026-11-18
- **dotnet.security.003** · MUST NOT · Use production secrets in development or test. · tags: secrets, config, tests · source: [Safe storage of app secrets in development](https://learn.microsoft.com/en-us/aspnet/core/security/app-secrets) · confirmed: base, 2026-11-18
- **dotnet.security.004** · SHOULD · Treat files under `wwwroot` as public, because `UseStaticFiles` performs no authorization. · tags: access, http · source: [ASP.NET Core middleware](https://learn.microsoft.com/en-us/aspnet/core/fundamentals/middleware/) · confirmed: base, 2026-11-18
- **dotnet.security.005** · MUST · Add `RequireAuthorization` to health check endpoints that expose detail, because `RequireHost` matches the spoofable `Host` header. · tags: access, health, http · source: [Health checks in ASP.NET Core](https://learn.microsoft.com/en-us/aspnet/core/host-and-deploy/health-checks) · confirmed: base, 2026-11-18
- **dotnet.security.006** · SHOULD · Run `dotnet format` only on trusted code, because it may restore, compile, and run analyzers from the project. · tags: formatting, access, build · source: [dotnet format](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet-format) · confirmed: base, 2026-11-18

## Performance

- **dotnet.performance.001** · The factory caches one handler per client name with a default lifetime of 2 minutes, so handlers are reused across `CreateClient` calls; disposing a client does not dispose its handler. · tags: http, lifecycle · source: [HttpClientFactory in .NET](https://learn.microsoft.com/en-us/dotnet/core/extensions/httpclient-factory) · confirmed: base, 2026-11-18
- **dotnet.performance.002** · `[LoggerMessage]` source generation is preferred over plain log extension calls for performance, and logger methods are synchronous, so queue slow log sinks to a background worker. · tags: logging · source: [Logging in .NET](https://learn.microsoft.com/en-us/dotnet/core/extensions/logging) · confirmed: base, 2026-11-18
- **dotnet.performance.003** · Keep DI factories fast and synchronous; resolving async work with `.Result` can deadlock, and `async` service resolution is not supported. · tags: di, async · source: [Dependency injection guidelines](https://learn.microsoft.com/en-us/dotnet/core/extensions/dependency-injection/guidelines) · confirmed: base, 2026-11-18
- **dotnet.performance.004** · Health checks run on every request to the endpoint, so keep them cheap (a connection check, or `SELECT 1`) and use a publisher for scheduled runs. · tags: health, data · source: [Health checks in ASP.NET Core](https://learn.microsoft.com/en-us/aspnet/core/host-and-deploy/health-checks) · confirmed: base, 2026-11-18

## Deployment and operations

- **dotnet.deploy.001** · The SDK builds container images without Docker; a local runtime is needed only to run the image or to publish into a local store. That is Docker or Podman, and from .NET 11 also `wslc` on Windows and Apple's `container` on macOS, which the SDK prefers when they are installed and running; `LocalRegistry` overrides the choice. · tags: image, build · source: [Containerize a .NET app reference](https://learn.microsoft.com/en-us/dotnet/core/containers/publish-configuration) · confirmed: base, 2026-11-22
- **dotnet.deploy.002** · The container image name defaults to the `AssemblyName`; set `ContainerRepository` in the project when that name is not a valid image name. · tags: image, config · source: [Containerize a .NET app with dotnet publish](https://learn.microsoft.com/en-us/dotnet/core/containers/sdk-publish) · confirmed: base, 2026-11-18
- **dotnet.deploy.003** · Exporting to a tarball with `ContainerArchiveOutputPath` needs no container daemon, which suits scanning pipelines. · tags: image, build · source: [Containerize a .NET app with dotnet publish](https://learn.microsoft.com/en-us/dotnet/core/containers/sdk-publish) · confirmed: base, 2026-11-18
- **dotnet.deploy.004** · In containers, set configuration through environment variables with `__` separators (for example `Logging__LogLevel__Default`), and set `DOTNET_USE_POLLING_FILE_WATCHER` to `1` when file-based reload must work on network shares or in Docker. · tags: config · source: [Options pattern in .NET](https://learn.microsoft.com/en-us/dotnet/core/extensions/options) · confirmed: base, 2026-11-18
- **dotnet.deploy.005** · Liveness and readiness probes map to health checks with `Predicate = _ => false` for liveness and a `ready` tag for readiness; `curl` is not in the .NET Linux images, so a `HEALTHCHECK` command needs another tool such as `wget` on Alpine. · tags: health, image · source: [Health checks in ASP.NET Core](https://learn.microsoft.com/en-us/aspnet/core/host-and-deploy/health-checks) · confirmed: base, 2026-11-18

## Our situation

- none yet

## Skills and agents

- `dev-workbook` - keeps this workbook; the dev skills read it through `workbook.py resolve`.
