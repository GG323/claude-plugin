#!/usr/bin/env bash
set -eu
cp -R "$(dirname "$0")/files/." .
chmod +x fakebin/kubectl fakebin/docker
git init -q
git add -A
git -c user.name=fixture -c user.email=fixture@example.invalid commit -q -m "shop api"

