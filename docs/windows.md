# Windows

T2 implements the worktree algorithm:

- `git rev-parse --path-format=absolute`
- `realpath` both git-dir and common-dir
- `\\` → `/`, strip trailing slash
- case-fold equality **only on Windows** when deciding main vs linked

There is still **no Windows CI row**. Do not treat Windows worktree identity as qualified until that exists.
