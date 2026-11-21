# Bulk discount for large orders: questions

| Round | # | Layer | Question | Recommended | Source | Evidence | Answer |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | details | Count items by quantity or by lines? | quantity | general | `Order.ItemCount` exists | recommended |
| 1 | 2 | details | Coupon and bulk together? | larger wins | general | no stacking rule in the code | recommended |

## Stated defaults

| Item | Default | Source |
| --- | --- | --- |
| Test framework | MSTest | `tests/Shop.Tests/Shop.Tests.csproj` |
