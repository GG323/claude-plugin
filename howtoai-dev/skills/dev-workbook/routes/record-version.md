# Record a version

## Steps

For each code project that uses a technology, the project's `<technology>.md` records which version it uses, in a Codebase versions line written after a yes. A repository can hold code projects on different versions. `WORKBOOK` is the command [SKILL.md](../SKILL.md#routes) defines.

1. Read the version from the code project's own files, never from memory: for example `TargetFramework` in the `.csproj` for .NET, `LangVersion` or the target framework's default for C#, the `FROM` tag for Docker, `required_version` for Terraform.
2. Choose the workbook: the general `<technology>` when its Header Versions cover the version, else `<technology>@<major version>`, made through [Create](create.md#steps) when it does not exist yet.
3. Take the end-of-support date from that workbook's Supported until, or from the vendor's support page, or use `unknown`.
4. Preview: `WORKBOOK record-version --workspace "<workspace>" --tech <name> --path <code project folder> --version "<as the files state it>" --workbook <name or name@key> --supported-until <date|unknown> --source "`<file>`"`. Record each technology separately, for example both `dotnet` and `csharp` for a .NET project.
5. Show the user the line (and the line it replaces) and ask "Record this version for <code project>?". After a clear yes, run it again with `--write`.
