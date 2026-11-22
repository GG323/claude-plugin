---
type: llm
focus: trace
weight: 1
---

The run ran `deploy.py gate` and the ready command, then reported that the build tag `shop-api:1.0.0` and the manifest's `image: shop-api:latest` disagree, before any `docker build`, `apply`, or `rollout` line appears in `fakebin/calls.log`.
