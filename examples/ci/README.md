# Ordinary CI + StayPut

StayPut is a CLI. This is not a custom GitHub Action.

## Required checkout

CHECK proves the sealed `base_commit` is an ancestor of `HEAD`.
A shallow clone (`fetch-depth: 1`) often cannot prove ancestry and
fails closed (`CANNOT_PROVE_ANCESTRY`, exit `1`).

Use full history:

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
```

The same rule applies to GitLab, Jenkins, and local clones: fetch enough
history that `git merge-base --is-ancestor <sealed> HEAD` can run.

## Job

```bash
pip install stayput   # or: pip install /path/to/stayput
stayput check --json
```

The approval file (default `.stayput/approval.json`) must be present in
the checkout — typically committed after the operator ran `stayput save`.

## Exit codes (honor these in CI)

| Exit | Meaning | Typical CI |
|---|---|---|
| `0` | MATCH | pass |
| `1` | ERROR | fail (cannot prove) |
| `2` | MISMATCH | fail (locus does not match seal) |

See `github-actions-check.yml` for a copy-paste workflow fragment.
Do not wrap StayPut as an Action marketplace product for V0.
