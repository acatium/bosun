# Deal-room refusals

**Date:** 2026-10-13 · **Caller:** the partner persona, calling `deal_room.create` directly (the same code the
MCP tool runs), signed in as the partner · Addresses redacted to `<persona>@<tenant>`.

| Case | Request | Result returned |
|---|---|---|
| A guest on a Confidential room | members: associate, the banker (a directory guest) | `refused`: "Cannot add <banker-guest>: Confidential stores never include people outside the firm. (rule: confidential-no-guests)" |
| The same guest, addressed by internal UPN (`...#EXT#@<tenant>`) | members: the banker's guest UPN | `refused`: same rule. Before the audit fix, this address passed as a member because guests were classified by email suffix. |
| Someone not in the directory | members: `nobody@<external>` | `refused`: "Cannot add nobody@<external>: not found in the firm's directory." |
| The Confidential label not yet available to the partner | a valid request | `refused`: "The Confidential label is not yet available to you, so no room was created. Newly published labels can take a few hours to reach people." No group was created (checked by directory query). |
| Resuming a room at a different sensitivity | a request naming an existing unlabelled room | `refused`: "Project Rehearsal already exists with a different sensitivity; it was not changed." |

Found while testing: with only `User.ReadBasic.All`, Microsoft Graph returns no `userType`, which would have
let every guest through. The app now holds `User.Read.All`, and anyone whose type cannot be read is refused.

The rule checks themselves are covered by offline tests in [`tests/test_model.py`](../../tests/test_model.py).
