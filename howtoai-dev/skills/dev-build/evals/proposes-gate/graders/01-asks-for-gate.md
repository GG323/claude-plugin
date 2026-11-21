---
type: llm
focus: trace
weight: 1
---

Before any code edit and before `build.py start`, the run asks the user to confirm a gate list that includes a format check in check mode (`dotnet format ... --verify-no-changes`) and a build or compile step, each with its source (the CI file or a workbook statement ID such as `dotnet.commands.002`), and proposes no command that changes files.
