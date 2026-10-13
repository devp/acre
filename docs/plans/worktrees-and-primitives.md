# acre: worktrees + agent-drivable primitives

## Context

Two problems, one plan.

**(1) Manual checkouts.** acre requires you to `gh pr checkout` before it runs, and
`contrib/scripts/acre-start.sh` works around that with one shared clone per repo at
`~/code/reviews/<repo>` that it force-checks-out to the default branch. You cannot review
two PRs of the same repo concurrently, and the script dirties your real checkout.

**Why not go `gh`-only instead:** `gh pr view --json` supplies metadata only
(`src/lib/sources/github.py:10`). Every byte of diff comes from local `git diff <base>..<head>`
(`src/lib/models.py:51-56` → `src/lib/sources/git.py:116-163`). `gh pr diff` could supply bytes,
but you'd lose `$EDITOR` open-at-file (`src/cli/util.py:21-48`), delta rendering,
`--focus-regex` over real files, and any reading of surrounding code — Job B's entire point.
Worktrees it is.

**(2) No shared state with the LLM.** You want a PR copilot and a terminal diff view in one
window. `~/.claude/skills/code-review-skim/SKILL.md` currently says *"The user tracks what's
reviewed; you don't"* — acre is exactly the shared state that sentence is missing. For pane
layout this genuinely is tmux with extra steps; the part tmux can't give you is Claude and
you reading/writing the same `.git/acre/<review-id>.json`. Build the shared state, not a
pane manager.

**Outcome:** `acre open 123` lands you in a review session with no manual git; the same
command hands an agent a path on stdout. acre gains `--json`, a non-prompting diff, and a
non-interactive mark — and ships a skill that teaches Claude Code to drive them.

**Decided, not open:** review state stays per-worktree and ephemeral (losing approvals on
teardown is intended, so `state.py` is untouched). Comments and everything after them live on
GH; acre's job is getting into a focused, explorable checkout fast. Phase 1 decisions below.

---

## Phase 1 — `acre open <pr-ref>` / `acre close`

**Scope now: Phase 1 only.** Phase 2 is deferred until real use shows a need for shared marks.

### Decided

- `acre` must be run inside the target repo. No repo discovery, no layout assumptions.
- `<pr-ref>` = `123` | `#123` | `https://github.com/owner/repo/pull/123`. URL owner/repo must
  match `gh repo view --json nameWithOwner`; mismatch → error (gh would otherwise fetch a
  foreign PR into this repo). Slug form lives only in `acre-start.sh`.
- Worktrees at `<main-root>/.acre-worktrees/pr-<N>`, hardcoded. On first use, write
  `.acre-worktrees/.gitignore` containing `*` (uv's venv trick; verified: `git status` clean in
  main and worktree). Nothing outside the dir is touched.
- `open` runs `interactive -y` in the worktree. No `overview`; run it on demand.
- `close` removes the worktree, keeps the local branch.
- Errors from gh/git (existing unregistered path, force-pushed PR, branch checked out
  elsewhere, dirty tree on remove) are surfaced as-is, no custom handling. Force-pushed PR:
  message hints `gh pr checkout <N> --force` inside the worktree.
- Built in a separate `../acre-next` worktree with `alias acre-next=…/acre-next/src/codereview.py`.
  The live `acre` alias (`~/.zshrc:46`) runs this checkout's working tree and stays untouched
  until Phase 1 merges. `acre-start.sh` keeps working throughout.

### Mechanics

**Main root:** `git rev-parse --path-format=absolute --git-common-dir` → `<main>/.git`, take
its parent. Verified from inside a linked worktree. (`get_repo_root()` returns the *current*
worktree, so it can't be used.)

**Provision:** `gh pr checkout <N> --worktree <abs-path>`, `cwd=main_root` (gh ≥ 2.102).
Verified in a scratch clone of `octocat/Hello-World`: fork PR lands on a real local branch so
`gh pr view` still infers the PR (`initialize.py:31` → `github.py:10` unchanged); rerun on an
existing worktree fetches + fast-forwards (reopen = refresh); works from inside another worktree.

**Enter:** `subprocess.run([sys.executable, abspath(argv[0]), "interactive", "-y"], cwd=path)`.
`src/codereview.py:19-28` binds `StateManager`/`review_id` to cwd before dispatch, so a
child process with the worktree as cwd gets `branch-<head>` and state in
`.git/worktrees/pr-N/acre/` via `StateManager._get_git_dir` (`state.py:36-52`). `main()` untouched.

**Close:** `git -C <main> worktree remove <path>`, then a `cd <main>` hint on stderr.

### Files

| File | Change |
|---|---|
| `src/lib/sources/git.py` | `get_main_worktree_root`, `worktree_remove`. |
| `src/lib/sources/github.py` | `pr_checkout_worktree(pr_number, path)`, `repo_name_with_owner()`. |
| `src/lib/worktree.py` *(new, pure)* | `parse_pr_ref`, `worktree_path_for_pr`; commit 3 adds `pr_number_from_path`. |
| `src/lib/commands/worktree.py` *(new)* | `impl_open`, `impl_close`, `register` — shaped like `simple_commands.py:89-110`. |
| `src/cli/parser.py` | register in `_build_argparse()`. Not in `interactive.py` → CLI-only. |

`init` untouched: `interactive -y` auto-inits (`interactive.py:99-105`).

### Thin `acre-start.sh`

Parses `<repo> <N>` | `owner/repo#N` | URL → `cd "${ACRE_REPOS_ROOT:-$HOME/code/reviews}/<repo>"`
→ `exec "$acre" open <N>`. Missing dir → error with a `gh repo clone` hint. Dirty checks,
default-branch checkout, `pull`, `init`, `overview` all go. Default root preserves today's layout.

### Commits

1. **`feat: acre open <pr-ref> provisions a worktree`** — helpers + command.
2. **`feat: acre close <N> removes a PR worktree`**.
3. **`enh: acre close infers the PR from cwd`** — `pr_number_from_path`.
4. *(after 1–3 merge to main)* **`enh: thin acre-start onto acre open`** + README command table.

### Tests

| File | Covers |
|---|---|
| `test_worktree_pr_ref.py` | `N`, `#N`, URL; URL repo mismatch → error; garbage → error. |
| `test_worktree_open.py` | monkeypatched `subprocess.run`: gh gets abs path + `cwd=main_root`; gh failure → `SystemExit`, no interactive child. |
| `test_worktree_path.py` *(commit 3)* | `pr_number_from_path` round-trip; `None` outside `.acre-worktrees`. |

**By hand:**
```sh
acre-next open <N>                  # interactive in .acre-worktrees/pr-N
git -C <main> status                # clean
acre-next open <other-N>            # concurrent second PR
acre-next open <url>                # via URL; foreign-repo URL → error
acre-next open <N>                  # reopen → ff refresh, state preserved
acre-next close <N>                 # removed, cd hint
cd .acre-worktrees/pr-<N> && acre-next close   # commit 3
```

---

## Phase 1b — sync "viewed" with GitHub, per file

Light, file-level only: acre's reviewed flag ↔ GH's per-file "Viewed" checkbox. Viewed state
is private to the viewer, so pushing it affects no one else. Independent of worktrees; lands
after Phase 1. Side effect: progress survives `close` → `open`, softening the "progress dies
with the worktree" cost.

### GitHub surface

No `gh pr` subcommand; GraphQL only:
- `markFileAsViewed` / `unmarkFileAsViewed`, input `{pullRequestId, path}`.
- Read: `pullRequest.files(first:100){nodes{path viewerViewedState} pageInfo{…}}` —
  `VIEWED` | `UNVIEWED` | `DISMISSED` (viewed, then the file changed). Paginate via
  `gh api graphql --paginate` with `$endCursor`.
- Pass `path` with **`-f`** (raw string), not `-F`. Verified in `gh api --help`: `-F` converts
  `true`/`false`/`null`/integers and reads `@file`, so a path like `123` or `@foo` would be
  mangled.
- Mutations need the PR node id: one `gh pr view N --json id` at init, stored in
  `state.metadata["pr_node_id"]` (metadata is a free-form dict; no schema change).

### Behavior

- **Push:** acre marks a file reviewed (`commands_v0.py:268`, skim mark-all `review.py:85`)
  → `markFileAsViewed`. `unapprove` → `unmarkFileAsViewed`. `reset` stays local.
- **Pull:** at `init` only, files `VIEWED` on GH → marked reviewed in acre. `UNVIEWED` and
  `DISMISSED` never unmark anything acre has. No pull per prompt.
- Only when `metadata["pr_number"]` exists; git-range reviews skip.
- gh failure → one-line warning on stderr; the local mark always wins and is never blocked.

### Commits

1. **`feat(github): read and set per-file viewed state`** — helpers in `sources/github.py`; test asserts `-f path=` and pagination args.
2. **`feat: push reviewed marks to GitHub viewed state`**.
3. **`feat: init pulls GitHub viewed files as reviewed`**.

### Open

- Default on, or opt-in via config? Lean default-on: private state, no flag to remember.
- Push latency: one `gh api` round-trip per mark inside the interactive loop. Sync call first;
  measure before considering a background process.

---

## Phase 2 — primitives + skill *(deferred)*

Revisit only if inline code-review-skim in a worktree leaves you wanting marks shared with a
second `acre interactive` tab. Before `mark-reviewed` lands, fix the lost-update race:
`CommandsV0.__init__` loads state once (`commands_v0.py:26`) and `cmd_review` saves that copy
after the "Mark reviewed?" prompt (`:268-269`; same at `review.py:85`) — reload before mark+save.
Skill becomes a "with acre" section in `code-review-skim`, not a separate `skills/acre`.

### The four surfaces

**`acre status --json`** — the shared-state read. `metadata` gives four keys and nothing about
files; `ls --raw` gives paths but not reviewed-flags, Δ-lines, or the index that
`review`/`mark-reviewed`/`preapprove` accept. That index is the join key between the model's
file numbering and acre's — emitting it makes them identical, so `code-review-skim`'s "number
the files yourself" becomes "acre numbers them."

Per-command `--json`, not global: a global flag must precede the subcommand, putting it at
`sys.argv[1]` where `_rewrite_args_via_aliases` (`codereview.py:12-16`) rewrites it.

**`acre review --no-prompt <item>`** — `--skim` still calls `yn("Approve all files?")`
(`commands/review.py:82`), which off a TTY hits `input()` at `util.py:10` with no `EOFError`
guard: traceback on closed stdin, hang otherwise. A flag on `review` rather than a new
`acre show` inherits `--focus-regex`, `--regex-include-context`, `--diff-line-numbers`,
`--hunk-numbers`, preapproval filtering and `diff_target` resolution for free.

**`acre mark-reviewed <items...>`** — the only path to `mark_file_reviewed` today is the
interactive prompt (`util.py:82-121` via `commands_v0.py:261-266`), while its inverse
`unapprove` is already batch. That asymmetry is what makes the workflow impossible.
Deliberately **not** named `approve` — `acre approve` approves the PR on GitHub
(`commands_v0.py:277-294`) and an agent reading `--help` must not be one token away from it.
Mirrors `unapprove.py`, reusing `_select_paths_to_review` (`review.py:9`).

**`acre ls --json` — cut.** `acre status --json | jq -r '.files[] | select(.reviewed|not) | .path'`
covers it, and it would need a mutex with `--raw`.

### JSON schema: `src/lib/state_view.py` *(new, pure)*

`review_state_view(state: ReviewState) -> dict` returning `review_id`, `diff_target`,
`metadata` (verbatim, so the skill needs one call not two), `progress`
(`files_total`/`files_reviewed`/`files_left`/`lines_total`/`lines_reviewed`/`percent`), and
`files[]` of `{index, path, lines, reviewed, preapproved_blocks}`.

A new module rather than a method on `ReviewState`: `save_state` (`state.py:57-85`) already
hand-rolls a serialization dict, and a sibling `to_json_dict()` invites someone to unify them —
coupling the agent-facing view to the on-disk format is the schema redesign that's off the
table. Matches the existing precedent of `diff_filter.py` / `hunk_filter.py` as pure modules
importing only `lib.models`.

- `preapproved_blocks` is a **count**, not ranges — the ranges are 1-based indices into
  *rendered diff output*, not source lines (`models.py:5-9`). A model will misread them.
- Omit `init_commit_sha`, `state.notes`, `FileState.notes`, `preapproved_sha` — the last two
  have no CLI writer / are dead, so they'd be permanent `null` noise.
- **`cmd_status` is restructured onto the same function** (`commands_v0.py:73-86`) so the
  human bar and the JSON percent cannot drift.
- Wiring trap: `interactive.py:115` calls `impl_status(context=context)` with **no `args`** —
  the signature must default and the read must be `getattr(args, "json", False)`.

### stderr + exit codes

One helper in `cli/util.py` (already the shared module every command imports):
`fail(message, code=1)` → stderr + `raise SystemExit` (`raise`, not `sys.exit`, because
existing tests assert with `pytest.raises(SystemExit)`).

Applied at seven sites: `commands_v0.py:28-29`, `simple_commands.py:54-55`,
`unapprove.py:10-11` and `:23-24`, `review.py:47-48`, `preapprove.py:63-64/68-69/78/83-84/91-92`,
`parser.py:65-66`. The four that currently `return` are the ones that matter — today
`acre review nonexistent.py` in an uninitialized repo **exits 0** with a message on stdout,
indistinguishable from success.

Plus `yn()` (`util.py:9-19`) gets an `EOFError` guard returning `False` — not `default` — so
a closed pipe can never auto-confirm a PR approval.

**Not converted:** `cmd_peek` (`commands_v0.py:119/124/128`) and `cmd_approve` (`:280/288/291`)
return `bool` and run inside the interactive prompt's `on_peek` callback (`:264`); exiting
would kill the loop. They're recoverable, not fatal.

### Color: tty-aware, no flag

`color_enabled(*, stream=None, env=None)` in `cli/pretty.py`: false off a tty, false under
`NO_COLOR`, true under `CLICOLOR_FORCE`. No `--color` flag — the whole point is that one
command serves both a human and an agent, and a flag means the skill must remember it every
call while the human must never type it. `CLICOLOR_FORCE` costs one line and buys back
`… | less -R`.

`--color=always` and `delta --color-only` stay load-bearing (git never colorizes into a pipe)
— they just become conditional at `git.py:120-145`. Two details: skip `delta` entirely when
color is off (its job here is syntax coloring; without it it's latency and reflow risk), and
pass `--no-color` explicitly rather than merely omitting `--color=always`, or a user's
`color.ui = always` leaks ANSI into the agent's context. Also gate `commands_v0.py:70`
(cyan test paths), `:80-81` (progress bar / whimsy), `:204,206` (dim line-number prefixes —
the flags the skill actually uses).

### The skill

**Location: `skills/acre/{SKILL.md,INSTALL.md}` in the acre repo — not `.claude/skills/`.**
A repo-local `.claude/skills/` loads only when cwd is that repo, and the PR copilot runs in
the *review target*, never in `~/code/acre` — so it must be symlinked regardless; putting it
under `.claude/` as well would double-load it whenever you work inside acre. Your six
existing skills already follow exactly this pattern (symlinks from `~/.claude/skills/` into
`~/code/prompts/{claude-skills,wip}/`), documented in `repo-bootstrap/INSTALL.md`. Mirror it:

```sh
ln -s ~/code/acre/skills/acre ~/.claude/skills/acre
```

Frontmatter uses `disable-model-invocation: true`, matching all six. The description ends
with the disambiguation clause your skills already use: *not a review method —
`code-review-skim` decides what to say about a file; this decides how to talk to acre about it.*

**Division of labor** — acre owns: which files are in the review and their indices; which are
reviewed (single source of truth); progress and Δ-lines; the diff bytes; preapproval. The
model owns: gist, decision count, findings, the comprehension check, which file to suggest next.

**Hard rules the skill states:**
- Re-read `acre status --json` at the top of every turn — you and the user's pane share one
  file and they may have marked things. Never cache the file list across turns.
- Always pass `--no-prompt` to `review`, or the Bash call hangs on stdin.
- Never run `acre approve` — that approves the PR on GitHub. `acre mark-reviewed` is the only
  write you make, and only on the user's say-so.
- Uninitialized → nonzero exit + stderr; tell the user to run `acre init`, don't run it.

**Fits the existing vocabulary** (`~/kb/notes/claude-context/PATTERNS.md`): this is **Job B**.
acre's `lines` is Δ-lines; **the decision count is yours** — branches, external calls, state
mutations, error paths — and say so when the two diverge.

**One change outside the repo, kept as a separate user-owned edit:**
`~/.claude/skills/code-review-skim/SKILL.md`'s "Progress" section — *"The user tracks what's
reviewed; you don't"* becomes a pointer to the acre skill.

### Commits

1. **`feat(status): add --json with a shared state view`** — `state_view.py` + flag +
   `cmd_status` restructured onto it. *Agent can read shared state.*
2. **`feat(review): add --no-prompt for batch-safe diffs`** — ~4 lines + a parser arg.
   *Agent can read a diff.*
3. **`feat: add CLI-only mark-reviewed command`** — ~30 lines mirroring `unapprove.py`.
   *Agent can write state. Loop closes here.*
4. **`fix: route command errors to stderr and exit nonzero`** — `fail()` + the seven sites +
   `yn()` EOF guard. *Makes 1–3 detectable by a script.*
5. **`enh: tty-aware color`** — `color_enabled()` threaded into `diff_lines` and four
   `commands_v0.py` sites. *Stops the agent paying tokens for ANSI.*
6. **`doc: ship the acre skill`** — `skills/acre/{SKILL.md,INSTALL.md}`, README for the new
   commands + JSON schema + `NO_COLOR`/`CLICOLOR_FORCE` + the symlink.

**Smallest viable spine if you want to stop early:** Phase 1 commits 1–2, Phase 2 commits 1–3.

---

## Verification

`just test` (= `PYTHONPATH=src uv run pytest`), `just typecheck`, `just lintcheck` green
before each commit — report actual output.

Test style: `src/tests/`, `monkeypatch`, `tmp_path`, driven through
`parse_args_from_cli(context=ctx, override_args=[...])`, asserting on `capsys`. Phase 1 tests
and by-hand checks are listed under Phase 1; Phase 2's are re-planned if it's picked up.

---

## Costs, stated

- Review progress dies with the worktree. Chosen — `acre close` then reopening starts over
  (until Phase 1b pulls GH viewed state back in at init).
- `git clean -xdf` in the main checkout now deletes worktrees. README caveat only.
- Worktree dir name is hardcoded; config added only if a repo collides with it.
- A PR whose branch is checked out elsewhere (your own PR in the main checkout) can't be
  opened in a worktree. Review it in place.

## Open

- None for Phase 1. Phase 1b has its own.
