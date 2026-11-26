---
type: llm
focus: trace
weight: 1
---

Before any test is written or run, the run asks the user whether to reproduce the bug. The question names the temporary test file and the command it would run as far as it is known (the CI test command, or "the project's test command"), and offers reproduce now, "I already reproduced it", or skip. The run then stops and waits.
