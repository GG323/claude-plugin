# Docker workbook

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
| Technology | `docker` |
| Title | Docker |
| Versions | Docker Engine (current) with BuildKit and Compose v2 |
| Version command | `docker --version` |
| Layer | base |
| Updated | 2026-11-18 |

Sources:

- [Building best practices](https://docs.docker.com/build/building/best-practices/) · checked 2026-11-18
- [Dockerfile reference](https://docs.docker.com/reference/dockerfile/) · checked 2026-11-18
- [Multi-stage builds](https://docs.docker.com/build/building/multi-stage/) · checked 2026-11-18
- [Build secrets](https://docs.docker.com/build/building/secrets/) · checked 2026-11-18
- [Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/) · checked 2026-11-18
- [Compose profiles](https://docs.docker.com/compose/how-tos/profiles/) · checked 2026-11-18
- [Docker Scout](https://docs.docker.com/scout/) · checked 2026-11-18
- [Compose services reference](https://docs.docker.com/reference/compose-file/services/) · checked 2026-11-18
- [docker compose down](https://docs.docker.com/reference/cli/docker/compose/down/) · checked 2026-11-18
- [docker scout cves](https://docs.docker.com/reference/cli/docker/scout/cves/) · checked 2026-11-18
- [docker scout recommendations](https://docs.docker.com/reference/cli/docker/scout/recommendations/) · checked 2026-11-18
- [hadolint](https://github.com/hadolint/hadolint) · checked 2026-11-18

## Load when

| Glob |
| --- |
| `**/Dockerfile` |
| `**/Dockerfile.*` |
| `**/*.dockerfile` |
| `**/.dockerignore` |
| `**/compose.yaml` |
| `**/compose.yml` |
| `**/docker-compose*.yml` |
| `**/docker-compose*.yaml` |

## Overview

- **docker.overview.001** · An image is built from a Dockerfile, which can hold several `FROM` stages so build tools stay out of the final image. · source: [Multi-stage builds](https://docs.docker.com/build/building/multi-stage/) · confirmed: base, 2026-11-18
- **docker.overview.002** · A Dockerfile is a list of instructions in which the order drives layer caching: frequently changing steps belong after stable ones. · source: [Building best practices](https://docs.docker.com/build/building/best-practices/) · confirmed: base, 2026-11-18
- **docker.overview.003** · Compose services can declare a `healthcheck` that works like the Dockerfile `HEALTHCHECK`, and Compose values override the image's. · source: [Compose services reference](https://docs.docker.com/reference/compose-file/services/) · confirmed: base, 2026-11-18
- **docker.overview.004** · Docker Scout inventories an image's components into an SBOM and checks them against a vulnerability database. · source: [Docker Scout](https://docs.docker.com/scout/) · confirmed: base, 2026-11-18

## Setup and configuration

- **docker.setup.001** · Name the ignore file `.dockerignore` and list irrelevant files in it to keep them out of the build context, using patterns similar to `.gitignore`. · source: [Building best practices](https://docs.docker.com/build/building/best-practices/) · confirmed: base, 2026-11-18
- **docker.setup.002** · A Compose `env_file` path resolves relative to the Compose file, and a missing file is an error unless `required: false` is set. · source: [Compose services reference](https://docs.docker.com/reference/compose-file/services/) · confirmed: base, 2026-11-18
- **docker.setup.003** · Values in a service's `environment` override values from `env_file`; with several env files in a list, the last file wins for duplicate keys. · source: [Compose services reference](https://docs.docker.com/reference/compose-file/services/) · confirmed: base, 2026-11-18
- **docker.setup.004** · Select profiled Compose services with `--profile <name>` or the `COMPOSE_PROFILES` variable (comma-separated). · source: [Compose profiles](https://docs.docker.com/compose/how-tos/profiles/) · confirmed: base, 2026-11-18

## Idioms and patterns

- **docker.patterns.001** · SHOULD · Pin the base image to a specific version tag, and to a digest where reproducible builds matter, and refresh pins with a tool such as Dependabot. · source: [Building best practices](https://docs.docker.com/build/building/best-practices/) · confirmed: base, 2026-11-18
- **docker.patterns.002** · MUST · Use multi-stage builds so compilers, package managers, and test tools stay in a builder stage and only runtime files are copied with `COPY --from`. · source: [Multi-stage builds](https://docs.docker.com/build/building/multi-stage/) · confirmed: base, 2026-11-18
- **docker.patterns.003** · SHOULD · Name stages with `AS name` and copy by that name, so reordering stages does not break `COPY --from`. · source: [Multi-stage builds](https://docs.docker.com/build/building/multi-stage/) · confirmed: base, 2026-11-18
- **docker.patterns.004** · MUST · Order instructions so stable steps come first: copy dependency manifests and install dependencies before copying the rest of the source. · source: [Building best practices](https://docs.docker.com/build/building/best-practices/) · confirmed: base, 2026-11-18
- **docker.patterns.005** · MUST · Run `apt-get update` and `apt-get install` in the same `RUN` instruction, and remove the apt lists in that instruction. · source: [Building best practices](https://docs.docker.com/build/building/best-practices/) · confirmed: base, 2026-11-18
- **docker.patterns.006** · SHOULD · Use exec (JSON array) form for `ENTRYPOINT` and `CMD`; use `ENTRYPOINT` for the fixed executable and `CMD` for default arguments. · source: [Dockerfile reference](https://docs.docker.com/reference/dockerfile/) · confirmed: base, 2026-11-18
- **docker.patterns.007** · SHOULD · Prefer `COPY` over `ADD` unless you need its URL fetch or automatic tar extraction. · source: [Dockerfile reference](https://docs.docker.com/reference/dockerfile/) · confirmed: base, 2026-11-18
- **docker.patterns.008** · SHOULD · Add a `HEALTHCHECK CMD ...` to long-running services; its exit code 0 means healthy and 1 unhealthy, and 2 is reserved. · source: [Dockerfile reference](https://docs.docker.com/reference/dockerfile/) · confirmed: base, 2026-11-18

## Pitfalls

- **docker.pitfalls.001** · Tags such as `latest` move over time, so builds change without a code change; spot it as a `FROM` line with no tag or with `:latest`. · source: [Building best practices](https://docs.docker.com/build/building/best-practices/) · confirmed: base, 2026-11-18
- **docker.pitfalls.002** · Shell-form `CMD` or `ENTRYPOINT` wraps the command in `/bin/sh -c`, so the app is not PID 1 and misses the SIGTERM from `docker stop`; spot it as a command written without brackets. · source: [Dockerfile reference](https://docs.docker.com/reference/dockerfile/) · confirmed: base, 2026-11-18
- **docker.pitfalls.003** · A bare `apt-get update` in its own `RUN` is cached and goes stale, so a later install can fail or use old indexes; spot it as `update` and `install` on separate lines. · source: [Building best practices](https://docs.docker.com/build/building/best-practices/) · confirmed: base, 2026-11-18
- **docker.pitfalls.004** · `ENV` values persist in the image and show in `docker inspect`, so a secret set with `ENV` leaks to anyone with the image. · source: [Dockerfile reference](https://docs.docker.com/reference/dockerfile/) · confirmed: base, 2026-11-18
- **docker.pitfalls.005** · `ARG` values are also unsafe for secrets; Docker advises against passing secrets as build arguments or environment variables. · source: [Build secrets](https://docs.docker.com/build/building/secrets/) · confirmed: base, 2026-11-18
- **docker.pitfalls.006** · The short form of `depends_on` (a list of names) does not wait for health; use the long form with `condition: service_healthy`. · source: [Compose services reference](https://docs.docker.com/reference/compose-file/services/) · confirmed: base, 2026-11-18
- **docker.pitfalls.007** · Only the last `HEALTHCHECK` in a Dockerfile takes effect, so a check added in a derived image replaces the base image's. · source: [Dockerfile reference](https://docs.docker.com/reference/dockerfile/) · confirmed: base, 2026-11-18
- **docker.pitfalls.008** · A numeric `COPY --chown` with no group sets the group to the same number, not the user's primary group; give both IDs explicitly. · source: [Dockerfile reference](https://docs.docker.com/reference/dockerfile/) · confirmed: base, 2026-11-18

## Commands

- **docker.commands.001** · Build with `docker build -t name:tag .`; add `--target <stage>` to stop at a stage, `--pull` to refresh base images, and `--no-cache` to ignore the layer cache. · source: [Multi-stage builds](https://docs.docker.com/build/building/multi-stage/) · confirmed: base, 2026-11-18
- **docker.commands.002** · Lint a Dockerfile with `hadolint Dockerfile`, or `docker run --rm -i hadolint/hadolint < Dockerfile`; `--failure-threshold warning` sets which severity gives a nonzero exit code. · source: [hadolint](https://github.com/hadolint/hadolint) · confirmed: base, 2026-11-18
- **docker.commands.003** · Silence one hadolint rule with `--ignore DL3006`, a `.hadolint.yaml` `ignored:` list, or a `# hadolint ignore=DL3006` comment above the instruction. · source: [hadolint](https://github.com/hadolint/hadolint) · confirmed: base, 2026-11-18
- **docker.commands.004** · Scan an image with `docker scout cves <image>`; `--only-severity critical,high` filters the report and `--exit-code` makes it exit with code 2 when vulnerabilities are found. · source: [docker scout cves](https://docs.docker.com/reference/cli/docker/scout/cves/) · confirmed: base, 2026-11-18
- **docker.commands.005** · Get base-image update advice with `docker scout recommendations <image>`; without an image it uses the most recently built one. · source: [docker scout recommendations](https://docs.docker.com/reference/cli/docker/scout/recommendations/) · confirmed: base, 2026-11-18
- **docker.commands.006** · Pass a build secret with `docker build --secret id=name,src=path .`, or `env=VAR` to read from an environment variable. · source: [Build secrets](https://docs.docker.com/build/building/secrets/) · confirmed: base, 2026-11-18
- **docker.commands.007** · `docker compose down` removes service containers and declared networks but keeps volumes; add `-v` to remove named and anonymous volumes and `--remove-orphans` to remove containers of services no longer in the file. · source: [docker compose down](https://docs.docker.com/reference/cli/docker/compose/down/) · confirmed: base, 2026-11-18

## Testing

- **docker.testing.001** · Start test dependencies with Compose and give each a `healthcheck`, so dependents can wait on `condition: service_healthy` instead of sleeping. · source: [Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/) · confirmed: base, 2026-11-18
- **docker.testing.002** · Use `depends_on` condition `service_completed_successfully` for one-shot setup services such as migrations that must finish before the app starts. · source: [Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/) · confirmed: base, 2026-11-18
- **docker.testing.003** · Mark test-only or debug services with `profiles` so a plain `docker compose up` leaves them off, and enable them with `--profile`. · source: [Compose profiles](https://docs.docker.com/compose/how-tos/profiles/) · confirmed: base, 2026-11-18
- **docker.testing.004** · Add a dedicated test stage in a multi-stage Dockerfile and build it with `--target`, so the production image carries no test tooling. · source: [Multi-stage builds](https://docs.docker.com/build/building/multi-stage/) · confirmed: base, 2026-11-18

## Security

- **docker.security.001** · MUST NOT · Put secrets in `ENV` or `ARG`; they remain in image layers or metadata. · source: [Build secrets](https://docs.docker.com/build/building/secrets/) · confirmed: base, 2026-11-18
- **docker.security.002** · MUST · Use `RUN --mount=type=secret,id=name` for build-time secrets, which appear at `/run/secrets/name` only during that instruction. · source: [Build secrets](https://docs.docker.com/build/building/secrets/) · confirmed: base, 2026-11-18
- **docker.security.003** · SHOULD · Use `RUN --mount=type=ssh` with `docker build --ssh` to clone private repositories without copying keys into the image. · source: [Build secrets](https://docs.docker.com/build/building/secrets/) · confirmed: base, 2026-11-18
- **docker.security.004** · SHOULD · Create and switch to a non-root user with `USER`, preferably with explicit numeric UID and GID, when the service needs no privileges. · source: [Building best practices](https://docs.docker.com/build/building/best-practices/) · confirmed: base, 2026-11-18
- **docker.security.005** · SHOULD · Use multi-stage output so the final image holds only what the app needs, which shrinks the attack surface and the number of packages to patch. · source: [Multi-stage builds](https://docs.docker.com/build/building/multi-stage/) · confirmed: base, 2026-11-18
- **docker.security.006** · SHOULD · Scan images for known vulnerabilities and review base-image recommendations with Docker Scout or an equivalent scanner. · source: [Docker Scout](https://docs.docker.com/scout/) · confirmed: base, 2026-11-18

## Performance

- **docker.performance.001** · SHOULD · Order instructions from least to most frequently changing so the cache is reused for as long as possible. · source: [Building best practices](https://docs.docker.com/build/building/best-practices/) · confirmed: base, 2026-11-18
- **docker.performance.002** · SHOULD · Exclude irrelevant files from the build context with `.dockerignore`. · source: [Building best practices](https://docs.docker.com/build/building/best-practices/) · confirmed: base, 2026-11-18
- **docker.performance.003** · With BuildKit, only the stages the target depends on are built; the legacy builder runs every stage up to the target. · source: [Multi-stage builds](https://docs.docker.com/build/building/multi-stage/) · confirmed: base, 2026-11-18
- **docker.performance.004** · Clear the apt lists in the same `RUN` that installs packages to keep the image small. · source: [Building best practices](https://docs.docker.com/build/building/best-practices/) · confirmed: base, 2026-11-18

## Deployment and operations

- **docker.deploy.001** · SHOULD · Pin deployed base images by digest where exact reproducibility is needed. · source: [Building best practices](https://docs.docker.com/build/building/best-practices/) · confirmed: base, 2026-11-18
- **docker.deploy.002** · SHOULD · Run the app in exec form and handle SIGTERM, the default stop signal; `STOPSIGNAL` changes it, and it applies to `docker stop`, not to Ctrl+C. · source: [Dockerfile reference](https://docs.docker.com/reference/dockerfile/) · confirmed: base, 2026-11-18
- **docker.deploy.003** · Healthcheck defaults are `--interval` 30s, `--timeout` 30s, `--start-period` 0s, and `--retries` 3; set a start period that covers real startup, since failures during it do not count toward retries. · source: [Dockerfile reference](https://docs.docker.com/reference/dockerfile/) · confirmed: base, 2026-11-18
- **docker.deploy.004** · A Compose `healthcheck` overrides the image's; `disable: true` or a `NONE` test turns off a check inherited from the image. · source: [Compose services reference](https://docs.docker.com/reference/compose-file/services/) · confirmed: base, 2026-11-18
- **docker.deploy.005** · Compose services without a `profiles` entry always start; profiled services start only when selected, or when named explicitly along with their dependencies. · source: [Compose profiles](https://docs.docker.com/compose/how-tos/profiles/) · confirmed: base, 2026-11-18

## Our situation

- none yet

## Skills and agents

- `dev-workbook` - keeps this workbook; the dev skills read it through `workbook.py resolve`.
