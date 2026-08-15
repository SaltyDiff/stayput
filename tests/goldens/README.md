# Golden vectors

These files freeze T1 canonical bytes / `record_digest` values and T4
instruction-byte digests for `stayput.snapshot.v0.1`.

They were regenerated once for the unpublished TaskPin → StayPut identity
migration. Schema string change alters canonical bytes and `record_digest`;
locus, path, instruction, and digest algorithms did not change.

Do not regenerate them to “fix” a later digest change. A changed golden
means canonicalization or instruction-digest semantics changed and needs
an explicit version decision.
