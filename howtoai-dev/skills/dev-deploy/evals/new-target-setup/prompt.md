---
tags: [dev-deploy]
max_turns: 60
timeout_seconds: 1800
allowed_tools: [Read, Glob, Grep, Skill, Bash, Write, Edit]
---

Fake docker and kubectl are in fakebin/ in the working folder: run every docker and kubectl command in Git Bash as `PATH="$PWD/fakebin:$PATH" <command>`. Each call is logged to fakebin/calls.log.

Deploy the shop API to my local Kubernetes.
