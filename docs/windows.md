# Windows

T2 implements the worktree algorithm:

- `git rev-parse --path-format=absolute`
- `realpath` both git-dir and common-dir
- `\\` → `/`, strip trailing slash
- case-fold equality **only on Windows** when deciding main vs linked

T3 path containment uses the same realpath-vs-toplevel rule. A symlink whose resolved target leaves the work tree is `PATH_OUTSIDE_ALLOWLIST`.

There is still **no Windows CI row**. Do not treat Windows worktree identity or symlink containment as qualified until that exists.
