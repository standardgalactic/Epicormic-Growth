# Epicormic Growth

This repository is an experiment in representing growth as Git history. A deterministic organism begins with one dormant trunk record. The supplied script can then produce 10,000 commits. Every commit appends exactly one immutable shoot to the canonical JSON Lines ledger and regenerates two derived views of the complete organism.

The commit sequence is intentionally excessive. Its scale is part of the work: the repository does not merely contain an image of accumulated growth; its history is the temporal structure that accumulated it.

## Inspect the plan

The script is safe by default. With no `--execute` flag it validates the repository and ledger, calculates the remaining work, previews the next shoots and exits without changing files.

```bash
python3 epicormic_growth.py
```

Run the test suite before beginning:

```bash
python3 -m unittest -v tests/test_epicormic_growth.py
```

## Begin or resume the 10,000-commit growth

This command commits locally and pushes every 250 successful growth commits:

```bash
python3 epicormic_growth.py --execute --target 10000 --push-every 250
```

To construct the entire history locally before a single final push, omit `--push-every` and push normally afterward:

```bash
python3 epicormic_growth.py --execute --target 10000
git push
```

Interruption is ordinary. Run the same command again and the script resumes from the last verified ledger record. It refuses to run with a dirty worktree, detached HEAD, a missing upstream when pushing is requested, a malformed or non-monotonic ledger, an altered hash chain, a target smaller than the current growth count, or unexpected staged changes.

The target counts generated shoots numbered 1 through 10,000. The dormant trunk is record 0 and belongs to this seed commit, so a complete run creates exactly 10,000 additional commits.

## Files

`growth/shoots.jsonl` is authoritative. Each line is canonical JSON and includes the SHA-256 hash of its payload plus the prior record hash. Existing lines must never change. `growth/organism.json` and `growth/organism.svg` are deterministic projections regenerated from the ledger on every growth commit. `growth/state.json` is a compact resumption and verification record.

The generator uses only the Python standard library and Git. It contains no dates or ambient randomness: the same seed and shoot number always produce the same parent, angle, length and color.

## Deliberate costs

Ten thousand commits will make clones, history traversal, hosting, and later repository maintenance unusually expensive. Repacking may compress repeated snapshots, but this is still repository-history bloat by design. The script never rewrites or deletes existing history; stopping early preserves a valid smaller organism.
