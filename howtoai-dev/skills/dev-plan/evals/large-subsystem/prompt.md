---
tags: [dev-plan]
max_turns: 200
timeout_seconds: 3600
allowed_tools: [Read, Glob, Grep, Skill, Bash, Write, Edit, Agent]
---

Use dev-plan to plan a new notifications subsystem: email and in-app notifications when an order ships or an export finishes, a queue so the API does not wait for sends, and rename users.email to users.contact_email because sign-in will move to usernames later. If you are asked questions, answer each with the recommended answer. Stop at the approval question.
