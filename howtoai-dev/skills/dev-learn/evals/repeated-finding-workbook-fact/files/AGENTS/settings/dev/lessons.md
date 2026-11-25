# Lessons

- **DL-001** · 2026-11-10 · stage: one-off · change: `2026-11-10-coupon-rounding` · finding: R1-C2 · where: `src/Shop/Orders/DiscountCalculator.cs` — The WELCOME10 discount was rounded to whole units because Math.Round was called on a decimal without a digits argument; fixed by hand in the build. Fix: none: one-off. Repeats: 1.
- **DL-002** · 2026-11-12 · stage: build · change: `2026-11-12-docker-base` · finding: R1-X1 · where: `Dockerfile` — The image ran as root because the Dockerfile had no USER line. Fix: docker workbook statement on non-root users, level 1. Repeats: 1.
