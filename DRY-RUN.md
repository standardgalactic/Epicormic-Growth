# Dry-run report

The seed ledger and all derived projections validate. The default invocation makes no changes and reports:

```text
verified shoots : 0
target commits  : 10000
remaining       : 10000
branch          : codex/epicormic-10000
next 00001       : parent 00000, angle -17.900, length 17.597
next 00002       : parent 00000, angle -8.672, length 9.630
next 00003       : parent 00001, angle -34.368, length 11.828
next 00004       : parent 00002, angle +31.405, length 10.502
next 00005       : parent 00004, angle -43.425, length 16.516
mode            : DRY RUN (pass --execute to create commits)
```

Five unit tests pass for deterministic generation, backward-only parentage, canonical ledger encoding, hash-chain tamper detection and reproducible projections.

A disposable-clone rehearsal created twelve sequential growth commits, resumed at precisely twelve shoots, retained thirteen ledger lines including the dormant trunk, left a clean worktree and passed `git fsck`.

A second disposable-clone rehearsal created 500 sequential growth commits in approximately seven seconds in the current Linux environment. Before repacking, its `.git` directory occupied approximately 42 MB; the authoritative ledger was 157,032 bytes, the JSON projection 198,465 bytes and the SVG projection 55,274 bytes. This short run verifies behavior but should not be treated as a linear forecast: later commits rewrite progressively larger projections, and pushing, automatic repacking, filesystem performance and hosting latency will dominate a complete 10,000-commit run.

The script remains inert until `--execute` is supplied. Its recommended network interval is 250 commits, producing at most forty routine batch pushes over the complete run.
