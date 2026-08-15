# StayPut usage

## Checks

`stayput check` compares the delivered Git locus to a sealed approval:

1. repository lineage
2. worktree identity
3. sealed base is an ancestor of `HEAD`
4. Git-visible delivered paths ⊆ `allowed_paths`
5. optional instruction-byte digest, only if sealed

## Does not check

Correctness, tests, intent, safety, data exfiltration, runtime, or whether
the model followed the prompt. Null `instruction_digest` skips instruction
verification.

## Save, then work, then check

```bash
stayput save --allowed-path src --allowed-path tests
# agent works
stayput check --json
```

Save is always explicit. Check never writes.

## `allowed_paths`

Literal prefixes. `.` allows any in-repo Git-visible path. Not a sandbox.

## Instruction file

```bash
stayput save --instruction-file PLAN.md --allowed-path src
stayput check --instruction-file PLAN.md --json
```

Exact bytes. Capture ≠ approve.

## Exit codes

`0` MATCH / success · `1` ERROR · `2` MISMATCH

## Hosts

Copy the matching example. Do not import a host SDK into StayPut.

- Claude Code: `examples/claude-code/`
- Cursor: `examples/cursor/`
- OpenHands: `examples/openhands/`
- CI: `examples/ci/` (full Git history required)
