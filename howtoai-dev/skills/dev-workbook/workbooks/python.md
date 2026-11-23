# Python workbook

## Contents

- [Header](#header)
- [Load when](#load-when)
- [Overview](#overview)
- [Setup and configuration](#setup-and-configuration)
- [Idioms and patterns](#idioms-and-patterns)
- [Pitfalls](#pitfalls)
- [Commands](#commands)
- [Testing](#testing)
- [Security](#security)
- [Performance](#performance)
- [Deployment and operations](#deployment-and-operations)
- [Our situation](#our-situation)
- [Skills and agents](#skills-and-agents)

## Header

| Key | Value |
| --- | --- |
| Technology | `python` |
| Title | Python |
| Versions | Python 3.11 to 3.15 |
| Supported until | 2027-10-01 |
| Version command | `python --version` (`py -3 --version` on Windows) |
| Layer | base |
| Updated | 2026-11-22 |

Sources:

- [sys.stdout](https://docs.python.org/3/library/sys.html#sys.stdout) · checked 2026-11-22
- [Python command line and environment](https://docs.python.org/3/using/cmdline.html#cmdoption-I) · checked 2026-11-22
- [re, regular expression operations](https://docs.python.org/3/library/re.html) · checked 2026-11-22
- [shutil, rmtree example](https://docs.python.org/3/library/shutil.html#rmtree-example) · checked 2026-11-22
- [unittest](https://docs.python.org/3/library/unittest.html#unittest.TestLoader.loadTestsFromModule) · checked 2026-11-22
- [Status of Python versions](https://devguide.python.org/versions/) · checked 2026-11-22

## Load when

| Glob |
| --- |
| `**/*.py` |
| `**/pyproject.toml` |

## Overview

- **python.overview.001** · Python 3.11 to 3.15 are supported on 2026-11-22. Each release gets about five years, and 3.10 ended in October 2026. · tags: versions · source: [Status of Python versions](https://devguide.python.org/versions/) · confirmed: base, 2026-11-22

## Setup and configuration

- **python.setup.001** · `-I` ignores every `PYTHON*` environment variable, `PYTHONUTF8` and `PYTHONIOENCODING` included. Pass `-X utf8` beside it, or set the encoding in code. · tags: cli, config · source: [Python command line and environment](https://docs.python.org/3/using/cmdline.html#cmdoption-I) · confirmed: base, 2026-11-22

## Idioms and patterns

- none yet

## Pitfalls

- **python.pitfalls.001** · On Windows before 3.15, standard output redirected to a file or pipe uses the ANSI code page unless UTF-8 mode or `PYTHONIOENCODING` overrides it, so printing a character outside that code page raises `UnicodeEncodeError`. Write ASCII-escaped JSON, or call `sys.stdout.reconfigure(encoding="utf-8")` at program start. · tags: strings, errors · source: [sys.stdout](https://docs.python.org/3/library/sys.html#sys.stdout) · confirmed: base, 2026-11-22
- **python.pitfalls.002** · `\s` matches line breaks too, so a pattern meant for one line can take the next. Match line by line, or use `[ \t]` for spaces and tabs within a line (`[^\S\n]` still matches `\r`). · tags: strings · source: [re, regular expression operations](https://docs.python.org/3/library/re.html) · confirmed: base, 2026-11-22
- **python.pitfalls.003** · `shutil.copytree` copies the read-only attribute, and `shutil.rmtree` fails on such an entry on Windows. Instead of `ignore_errors=True`, pass a handler that runs `os.chmod(path, stat.S_IWRITE)` and retries, as `onexc` from 3.12 or as `onerror` on 3.11. · tags: errors, config · source: [shutil, rmtree example](https://docs.python.org/3/library/shutil.html#rmtree-example) · confirmed: base, 2026-11-22

## Commands

- none yet

## Testing

- **python.testing.001** · A `unittest.TestCase` subclass inherits the `test` methods it does not override, so they run again when the parent is collected too. Share helpers through a base class or mixin without tests, or through plain functions. · tags: tests · source: [unittest](https://docs.python.org/3/library/unittest.html#unittest.TestLoader.loadTestsFromModule) · confirmed: base, 2026-11-22

## Security

- none yet

## Performance

- none yet

## Deployment and operations

- none yet

## Our situation

- none yet

## Skills and agents

- `dev-workbook` - keeps this workbook; the dev skills read it through `workbook.py resolve`.
