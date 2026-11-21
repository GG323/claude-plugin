#!/usr/bin/env bash
set -eu
cp -R "$(dirname "$0")/files/." .
git init -q
git add -A
git -c user.name=fixture -c user.email=fixture@example.invalid commit -q -m "bulk discount: plan and failing tests"
