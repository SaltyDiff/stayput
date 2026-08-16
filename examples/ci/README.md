# Ordinary CI + StayPut

StayPut is a CLI. This is not a custom GitHub Action.

## Required checkout

CHECK inspects the repository before it compares locus. A shallow clone
(`fetch-depth: 1`) fails closed as `SHALLOW_REPOSITORY` (ERROR, exit `1`).
StayPut does not attempt ancestry in a shallow repository.

Use full history:

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
```

The same rule applies to GitLab, Jenkins, and local clones: do not check
out a shallow repository. If Git is not shallow but
`git merge-base --is-ancestor <sealed> HEAD` still cannot decide, that
is `CANNOT_PROVE_ANCESTRY` (also ERROR, exit `1`) — not a MISMATCH.

## Job

```bash
pip install stayput   # or: pip install /path/to/stayput
stayput check --json
```

Honor the **process exit code**. Do not gate the job on JSON
`"ok": true`. A MISMATCH result is also `"ok": true` with
`"status": "MISMATCH"` and exit `2`. See [`docs/failures.md`](../../docs/failures.md).

The approval file (default `.stayput/approval.json`) must be present in
the checkout — typically committed after the operator ran `stayput save`.

## Exit codes (honor these in CI)

| Exit | Meaning | Typical CI |
|---|---|---|
| `0` | MATCH | pass |
| `1` | ERROR | fail (cannot prove, including shallow clone) |
| `2` | MISMATCH | fail (locus does not match seal) |

See `github-actions-check.yml` for a copy-paste workflow fragment.
Do not wrap StayPut as an Action marketplace product for V0.
