#!/usr/bin/env bash
set -eu
cp -R "$(dirname "$0")/files/." .
git init -q
git add -A
git -c user.name=test -c user.email=test@example.com commit -qm "AB#42 Add bulk discount"
git remote add origin https://dev.azure.com/contoso/Shop/_git/shop
