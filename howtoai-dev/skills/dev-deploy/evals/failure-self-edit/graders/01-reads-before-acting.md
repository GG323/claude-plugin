---
type: llm
focus: trace
weight: 1
---

After the failed rollout, `fakebin/calls.log` shows a `describe`, `get events`, or `get pods` call before the `rollout undo` call, and no second `apply`.
