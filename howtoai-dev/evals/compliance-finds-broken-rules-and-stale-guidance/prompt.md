---
tags: [howtoai-dev]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, WebSearch, WebFetch, Agent]
---

Use the goldfish-compliance agent to review plan.md in this repository. Review kind: plan. No workbook statements and no workbook audit are supplied. freshness: on. Use the findings prefix P1-W.

Input files: plan.md, AGENTS.md, README.md, src/Api/Api.csproj, src/Api/Orders/RefundService.cs, tests/Api.Tests/RefundServiceTests.cs, db/migrations/001_orders.sql
