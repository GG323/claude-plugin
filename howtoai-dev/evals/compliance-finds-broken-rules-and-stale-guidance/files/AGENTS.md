# Acme orders service

## Contents

- [Conventions](#conventions)
- [Skills and agents](#skills-and-agents)

## Conventions

- Target framework: .NET 8 (`net8.0`) for every project.
- Tests live in `tests/<Project>.Tests/`, one xUnit project per source project; never under `src/`.
- Log through `ILogger<T>`; never `Console.WriteLine` in service code.
- Database migrations are numbered SQL files in `db/migrations/` (`NNN_name.sql`), applied by the deploy pipeline.
- Run `dotnet format --verify-no-changes` before a change is done.

## Skills and agents

None.
