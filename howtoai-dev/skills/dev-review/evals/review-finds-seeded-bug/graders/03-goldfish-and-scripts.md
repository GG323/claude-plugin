---
type: llm
focus: trace
weight: 1
---

The run started fresh subagents for the reviewers (spec first, then at least correctness and tests), the scorer, and the verifier, each briefed only with the files their Input lists; it ran `review.py diff`, `review.py receipts`, `findings.py collect --kind code`, and `findings.py tally` with `--changed` and `--inspection`.
