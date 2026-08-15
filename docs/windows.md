# Windows

T1 contains no Git or filesystem projection.

Later Git locus work (T2+) may need `--path-format=absolute`, `\` → `/` normalization, and case-fold equality for main-worktree detection. That behavior is **not qualified** in T1 and is explicitly deferred until a Windows test row exists or a later release documents remaining uncertainty.

Do not assume Windows worktree identity is proven by this package version.
