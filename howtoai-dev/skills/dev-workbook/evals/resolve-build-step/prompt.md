---
tags: [dev-workbook]
max_turns: 25
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Bash]
---

dev-build asks dev-workbook to Resolve for its build step: it changes src/Api/Program.cs and Dockerfile and needs Idioms and patterns, Pitfalls, and Commands. There is no change folder.

Input files: AGENTS.md, Dockerfile, src/Api/Program.cs, src/Api/Api.csproj, infra/main.tf
