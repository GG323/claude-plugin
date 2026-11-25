# Terraform workbook

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

## Header

| Key | Value |
| --- | --- |
| Technology | `terraform` |
| Title | Terraform |
| Versions | Terraform 1.x |
| Version command | `terraform version` |
| Layer | base |
| Updated | 2026-11-22 |

Sources:

- [Terraform style guide](https://developer.hashicorp.com/terraform/language/style) · checked 2026-11-18
- [Remote state](https://developer.hashicorp.com/terraform/language/state/remote) · checked 2026-11-18
- [Standard module structure](https://developer.hashicorp.com/terraform/language/modules/develop/structure) · checked 2026-11-18
- [Tests](https://developer.hashicorp.com/terraform/language/tests) · checked 2026-11-18
- [Dependency lock file](https://developer.hashicorp.com/terraform/language/files/dependency-lock) · checked 2026-11-18
- [Refactoring](https://developer.hashicorp.com/terraform/language/modules/develop/refactoring) · checked 2026-11-18
- [Sensitive variables](https://developer.hashicorp.com/terraform/tutorials/configuration-language/sensitive-variables) · checked 2026-11-18
- [terraform plan](https://developer.hashicorp.com/terraform/cli/commands/plan) · checked 2026-11-18
- [for_each](https://developer.hashicorp.com/terraform/language/meta-arguments/for_each) · checked 2026-11-18
- [count](https://developer.hashicorp.com/terraform/language/meta-arguments/count) · checked 2026-11-18
- [Import](https://developer.hashicorp.com/terraform/language/import) · checked 2026-11-18
- [S3 backend](https://developer.hashicorp.com/terraform/language/backend/s3) · checked 2026-11-18
- [CLI workspaces](https://developer.hashicorp.com/terraform/cli/workspaces) · checked 2026-11-18
- [terraform test](https://developer.hashicorp.com/terraform/cli/commands/test) · checked 2026-11-18
- [terraform fmt](https://developer.hashicorp.com/terraform/cli/commands/fmt) · checked 2026-11-18
- [terraform validate](https://developer.hashicorp.com/terraform/cli/commands/validate) · checked 2026-11-18
- [terraform-skill](https://github.com/antonbabenko/terraform-skill) · checked 2026-11-18 · Apache 2.0, secondary source
- [Output block reference](https://developer.hashicorp.com/terraform/language/block/output) · checked 2026-11-22
- [Terraform 1.15 changelog](https://raw.githubusercontent.com/hashicorp/terraform/v1.15/CHANGELOG.md) · checked 2026-11-22

## Load when

| Glob |
| --- |
| `**/*.tf` |
| `**/*.tfvars` |
| `**/*.tftest.hcl` |
| `**/.terraform.lock.hcl` |

## Overview

- **terraform.overview.001** · `terraform plan` previews the changes Terraform would make, and `-out` saves that plan so a later `terraform apply` can run exactly it. · tags: cli, state · source: [terraform plan](https://developer.hashicorp.com/terraform/cli/commands/plan) · confirmed: base, 2026-11-18
- **terraform.overview.002** · State can live in a shared remote data store instead of a local `terraform.tfstate`, so team members work from the same state. · tags: state · source: [Remote state](https://developer.hashicorp.com/terraform/language/state/remote) · confirmed: base, 2026-11-18
- **terraform.overview.003** · A module is a directory of Terraform files; the root module is the entrypoint and can call nested modules from `modules/` or external sources. · tags: modules · source: [Standard module structure](https://developer.hashicorp.com/terraform/language/modules/develop/structure) · confirmed: base, 2026-11-18
- **terraform.overview.004** · Mock providers for tests exist from Terraform 1.7. · tags: tests, versions · source: [Tests](https://developer.hashicorp.com/terraform/language/tests) · confirmed: base, 2026-11-18

## Setup and configuration

- **terraform.setup.001** · SHOULD · Declare `required_version` and pin each provider in `required_providers` with a version constraint, usually kept in `terraform.tf`. · tags: versions, dependencies · source: [Terraform style guide](https://developer.hashicorp.com/terraform/language/style) · confirmed: base, 2026-11-18
- **terraform.setup.002** · SHOULD · Split a root module into `main.tf`, `providers.tf`, `backend.tf`, `variables.tf`, `outputs.tf`, and `locals.tf`, and group larger configurations by logical area such as networking or compute. · tags: modules, style · source: [Terraform style guide](https://developer.hashicorp.com/terraform/language/style) · confirmed: base, 2026-11-18
- **terraform.setup.003** · Plain `terraform init` reinstalls the provider versions recorded in `.terraform.lock.hcl`; `init -upgrade` selects the newest versions allowed by the constraints. · tags: dependencies, versions · source: [Dependency lock file](https://developer.hashicorp.com/terraform/language/files/dependency-lock) · confirmed: base, 2026-11-18
- **terraform.setup.004** · MUST · Commit `.terraform.lock.hcl` so dependency changes go through code review. · tags: dependencies, versions · source: [Dependency lock file](https://developer.hashicorp.com/terraform/language/files/dependency-lock) · confirmed: base, 2026-11-18
- **terraform.setup.005** · SHOULD · Name resources with short descriptive nouns in snake_case and do not repeat the resource type in the name. · tags: style · source: [Terraform style guide](https://developer.hashicorp.com/terraform/language/style) · confirmed: base, 2026-11-18
- **terraform.setup.006** · MUST · Keep `*.tfvars` files that hold secrets out of version control; the common Terraform `.gitignore` ignores them. · tags: secrets, config · source: [Sensitive variables](https://developer.hashicorp.com/terraform/tutorials/configuration-language/sensitive-variables) · confirmed: base, 2026-11-18
- **terraform.setup.007** · Terraform reads input values from `TF_VAR_<name>` environment variables, which can persist in the shell environment and command history. · tags: config, secrets · source: [Sensitive variables](https://developer.hashicorp.com/terraform/tutorials/configuration-language/sensitive-variables) · confirmed: base, 2026-11-18

## Idioms and patterns

- **terraform.patterns.001** · MUST · Use `for_each` over a map or a set of strings for collections of resources; instances are addressed by stable keys, and lists need `toset()`. · tags: state, style · source: [for_each](https://developer.hashicorp.com/terraform/language/meta-arguments/for_each) · confirmed: base, 2026-11-18
- **terraform.patterns.002** · MUST NOT · Use `count` for a collection whose items may be added or removed in the middle: instances are identified by index, so the mapping to real objects can shift. · tags: state, style · source: [count](https://developer.hashicorp.com/terraform/language/meta-arguments/count) · confirmed: base, 2026-11-18
- **terraform.patterns.003** · SHOULD · Use `count` for near-identical instances or an on/off toggle such as `count = var.enabled ? 1 : 0`. · tags: style, config · source: [count](https://developer.hashicorp.com/terraform/language/meta-arguments/count) · confirmed: base, 2026-11-18
- **terraform.patterns.004** · MUST · Give every variable a `type` and `description` and every output a `description`, and mark secrets and outputs derived from them `sensitive = true`. Give an output a `type` too where `required_version` is 1.15 or later, the first version that takes one. · tags: secrets, style · source: [Terraform style guide](https://developer.hashicorp.com/terraform/language/style), [Terraform 1.15 changelog](https://raw.githubusercontent.com/hashicorp/terraform/v1.15/CHANGELOG.md) · confirmed: base, 2026-11-22
- **terraform.patterns.005** · SHOULD · Follow the standard module layout: root `main.tf`, `variables.tf`, `outputs.tf`, a `README.md`, nested modules under `modules/`, and samples under `examples/`. · tags: modules, style · source: [Standard module structure](https://developer.hashicorp.com/terraform/language/modules/develop/structure) · confirmed: base, 2026-11-18
- **terraform.patterns.006** · SHOULD · Keep modules composable: callers combine them instead of modules calling each other in deep trees. · tags: modules · source: [Standard module structure](https://developer.hashicorp.com/terraform/language/modules/develop/structure) · confirmed: base, 2026-11-18
- **terraform.patterns.007** · MUST · Pin registry module versions and provider versions. · tags: versions, dependencies, modules · source: [Terraform style guide](https://developer.hashicorp.com/terraform/language/style) · confirmed: base, 2026-11-18
- **terraform.patterns.008** · MUST · Use `moved` blocks when renaming a resource or module or switching between `count` and `for_each`, so Terraform renames the state object instead of destroying and recreating it. · tags: state, modules · source: [Refactoring](https://developer.hashicorp.com/terraform/language/modules/develop/refactoring) · confirmed: base, 2026-11-18

## Pitfalls

- **terraform.pitfalls.001** · Unpinned providers or registry modules; spot it by missing `required_providers` versions or a registry module without `version`. · tags: versions, dependencies · source: [Terraform style guide](https://developer.hashicorp.com/terraform/language/style) · confirmed: base, 2026-11-18
- **terraform.pitfalls.002** · Renaming a resource or module without a `moved` block; configurations still using the old address plan to delete the object. · tags: state · source: [Refactoring](https://developer.hashicorp.com/terraform/language/modules/develop/refactoring) · confirmed: base, 2026-11-18
- **terraform.pitfalls.003** · Using `count` over a list; instances are identified by index, so a change to the list can change which object each index maps to. · tags: state · source: [count](https://developer.hashicorp.com/terraform/language/meta-arguments/count) · confirmed: base, 2026-11-18
- **terraform.pitfalls.004** · Local state used for shared infrastructure; spot it by a `terraform.tfstate` file in the repository and no `backend` block, where a shared remote store would give everyone the same state. · tags: state · source: [Remote state](https://developer.hashicorp.com/terraform/language/state/remote) · confirmed: base, 2026-11-18
- **terraform.pitfalls.005** · Believing `sensitive = true` secures a value: it redacts CLI output and logs, but local state files still store the value in plain text. · tags: secrets, state · source: [Sensitive variables](https://developer.hashicorp.com/terraform/tutorials/configuration-language/sensitive-variables) · confirmed: base, 2026-11-18
- **terraform.pitfalls.006** · Overusing `-target`; the docs say to use it only in exceptional cases, since it can hide configuration drift. · tags: state, cli · source: [terraform plan](https://developer.hashicorp.com/terraform/cli/commands/plan) · confirmed: base, 2026-11-18
- **terraform.pitfalls.007** · Running `init -upgrade` without meaning to; it ignores recorded selections and can change the lock file; spot it by an unexpected `.terraform.lock.hcl` diff. · tags: versions, dependencies, cli · source: [Dependency lock file](https://developer.hashicorp.com/terraform/language/files/dependency-lock) · confirmed: base, 2026-11-18
- **terraform.pitfalls.008** · Removing a historical `moved` block from a shared module is a breaking change for callers still on the old address. · tags: modules, state, versions · source: [Refactoring](https://developer.hashicorp.com/terraform/language/modules/develop/refactoring) · confirmed: base, 2026-11-18

## Commands

- **terraform.commands.001** · `terraform init` installs providers and modules and records provider checksums in the lock file; `-upgrade` selects newer versions within the constraints. · tags: dependencies, cli, build · source: [Dependency lock file](https://developer.hashicorp.com/terraform/language/files/dependency-lock) · confirmed: base, 2026-11-18
- **terraform.commands.002** · `terraform fmt -recursive -check -diff` reports formatting differences in subdirectories without changing files and exits non-zero if any exist; leave out `-check` to rewrite files. · tags: formatting, cli, build · source: [terraform fmt](https://developer.hashicorp.com/terraform/cli/commands/fmt) · confirmed: base, 2026-11-18
- **terraform.commands.003** · `terraform validate` checks syntax and internal consistency without contacting remote services; it needs an initialized directory, and `terraform init -backend=false` initializes without the backend. · tags: linting, cli, build · source: [terraform validate](https://developer.hashicorp.com/terraform/cli/commands/validate) · confirmed: base, 2026-11-18
- **terraform.commands.004** · `terraform plan -out=tfplan -input=false -var-file=<file>.tfvars` saves a plan without prompting; `-detailed-exitcode` returns 0 for no changes, 1 for an error, and 2 for changes. · tags: cli, state, build · source: [terraform plan](https://developer.hashicorp.com/terraform/cli/commands/plan) · confirmed: base, 2026-11-18
- **terraform.commands.005** · `terraform apply tfplan` runs a saved plan; avoid `-lock=false`, which skips the state lock. · tags: cli, state · source: [terraform plan](https://developer.hashicorp.com/terraform/cli/commands/plan) · confirmed: base, 2026-11-18
- **terraform.commands.006** · `terraform plan -refresh-only` updates state and outputs to match changes made outside Terraform, and `terraform plan -destroy` previews destroying all managed objects. · tags: cli, state · source: [terraform plan](https://developer.hashicorp.com/terraform/cli/commands/plan) · confirmed: base, 2026-11-18
- **terraform.commands.007** · `terraform providers lock -platform=<os>_<arch>` records checksums for other platforms, one `-platform` flag per platform. · tags: dependencies, cli · source: [Dependency lock file](https://developer.hashicorp.com/terraform/language/files/dependency-lock) · confirmed: base, 2026-11-18
- **terraform.commands.008** · `terraform test` runs the tests; `-filter=<file>` limits test files, `-verbose` prints the plan or state per run, `-json` gives machine-readable output, and `-test-directory=<dir>` overrides the default `tests`. · tags: tests, cli · source: [terraform test](https://developer.hashicorp.com/terraform/cli/commands/test) · confirmed: base, 2026-11-18

## Testing

- **terraform.testing.001** · Tests live in `*.tftest.hcl` or `*.tftest.json` files with one or more `run` blocks, which execute sequentially by default. · tags: tests · source: [Tests](https://developer.hashicorp.com/terraform/language/tests) · confirmed: base, 2026-11-18
- **terraform.testing.002** · MUST · Set `command = plan` in test `run` blocks that should create nothing; the default, `apply`, creates real infrastructure. · tags: tests, state · source: [Tests](https://developer.hashicorp.com/terraform/language/tests) · confirmed: base, 2026-11-18
- **terraform.testing.003** · Each `assert` block needs a `condition` and an `error_message`, and conditions can reference outputs from earlier runs. · tags: tests · source: [Tests](https://developer.hashicorp.com/terraform/language/tests) · confirmed: base, 2026-11-18
- **terraform.testing.004** · `expect_failures` lists checkable objects, such as variable validations, that are expected to fail; the docs recommend it mainly with `command = plan`. · tags: tests, errors · source: [Tests](https://developer.hashicorp.com/terraform/language/tests) · confirmed: base, 2026-11-18
- **terraform.testing.005** · A `run` block can set `variables`, `plan_options`, and a `module` block, and run-level variables override file-level ones. · tags: tests, modules · source: [Tests](https://developer.hashicorp.com/terraform/language/tests) · confirmed: base, 2026-11-18
- **terraform.testing.006** · `terraform test` limits plan and apply operations with `-parallelism` and run blocks with `-run-parallelism`, both defaulting to 10. · tags: tests, performance · source: [terraform test](https://developer.hashicorp.com/terraform/cli/commands/test) · confirmed: base, 2026-11-18

## Security

- **terraform.security.001** · MUST NOT · Commit secrets in `.tfvars` files; supply them through `TF_VAR_` variables or a secret manager such as HashiCorp Vault. · tags: secrets · source: [Sensitive variables](https://developer.hashicorp.com/terraform/tutorials/configuration-language/sensitive-variables) · confirmed: base, 2026-11-18
- **terraform.security.002** · MUST · Mark secret variables and any output derived from them `sensitive = true`. · tags: secrets · source: [Sensitive variables](https://developer.hashicorp.com/terraform/tutorials/configuration-language/sensitive-variables) · confirmed: base, 2026-11-18
- **terraform.security.003** · MUST · Protect state files: they store values in plain text even for sensitive variables, so use an access-controlled remote store such as HCP Terraform. · tags: secrets, state, access · source: [Sensitive variables](https://developer.hashicorp.com/terraform/tutorials/configuration-language/sensitive-variables) · confirmed: base, 2026-11-18
- **terraform.security.004** · MUST · Treat saved plan files as secrets: they can contain sensitive values in cleartext. · tags: secrets, state · source: [terraform plan](https://developer.hashicorp.com/terraform/cli/commands/plan) · confirmed: base, 2026-11-18
- **terraform.security.005** · SHOULD · Scan Terraform code with Trivy and Checkov. · tags: linting, access · source: [terraform-skill](https://github.com/antonbabenko/terraform-skill) · confirmed: base, 2026-11-18

## Performance

- **terraform.performance.001** · Remote state can expose output values to other configurations, so infrastructure can be split into smaller components. · tags: state, modules · source: [Remote state](https://developer.hashicorp.com/terraform/language/state/remote) · confirmed: base, 2026-11-18
- **terraform.performance.002** · `terraform test` defaults to 10 parallel plan or apply operations per run and 10 parallel run blocks per file, tunable with `-parallelism` and `-run-parallelism`. · tags: tests, performance · source: [terraform test](https://developer.hashicorp.com/terraform/cli/commands/test) · confirmed: base, 2026-11-18

## Deployment and operations

- **terraform.deploy.001** · MUST · Keep shared state in a remote backend such as S3, Azure Blob Storage, Google Cloud Storage, or HCP Terraform, and use one that supports state locking. · tags: state, access · source: [Remote state](https://developer.hashicorp.com/terraform/language/state/remote) · confirmed: base, 2026-11-18
- **terraform.deploy.002** · SHOULD · On the S3 backend, set `use_lockfile = true` for locking; `dynamodb_table` locking is deprecated. Enable bucket versioning and `encrypt` as well. · tags: state, access, config · source: [S3 backend](https://developer.hashicorp.com/terraform/language/backend/s3) · confirmed: base, 2026-11-18
- **terraform.deploy.003** · Workspaces share one configuration and one backend, so they suit temporary copies; environments needing different credentials or access controls belong in separate configurations with their own backends. · tags: state, config, access · source: [CLI workspaces](https://developer.hashicorp.com/terraform/cli/workspaces) · confirmed: base, 2026-11-18
- **terraform.deploy.004** · SHOULD · In CI, save the plan with `plan -out` and apply that same saved plan file. · tags: build, cli, state · source: [terraform plan](https://developer.hashicorp.com/terraform/cli/commands/plan) · confirmed: base, 2026-11-18
- **terraform.deploy.005** · An `import` block names the real object's ID and the resource address; with a matching `resource` block, `terraform apply` imports it, and `terraform plan -generate-config-out=<file>` can write the resource block. · tags: state, cli · source: [Import](https://developer.hashicorp.com/terraform/language/import) · confirmed: base, 2026-11-18
- **terraform.deploy.006** · When splitting a module, publish the new modules and a shim that calls them with `moved` blocks, and mark the old module deprecated. · tags: modules, state · source: [Refactoring](https://developer.hashicorp.com/terraform/language/modules/develop/refactoring) · confirmed: base, 2026-11-18

## Our situation

- none yet
