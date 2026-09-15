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
- `<pr-ref>` = `123` | `#123` | `owner/repo#123` | `https://github.com/owner/repo/pull/123`.
  Slug/URL forms must match the current repo's `gh repo view --json nameWithOwner`; mismatch →
  error. (gh would otherwise fetch a foreign PR into this repo.)
- Worktrees at `<main-root>/.acre-worktrees/pr-<N>`, configurable via `[worktree] dir`;
  `/<dir>/` written to `.git/info/exclude`.
- `open` execs `interactive -y`. No `overview`; run it on demand.
- `close` in scope: removes the worktree, keeps the local branch.
- Force-pushed PR on reopen → surface gh's error, hint `acre open <N> --force` (passes
  `--force` to gh, resets the local branch). Never reset implicitly.
- Built in a separate `../acre-next` worktree with `alias acre-next=…/acre-next/src/codereview.py`.
  The live `acre` alias (`~/.zshrc:46`) points at this checkout's `main` and stays untouched
  until Phase 1 merges. `acre-start.sh` keeps working throughout.

### Key decision: re-exec, don't refactor startup

`src/codereview.py:19-28` builds `StateManager` and resolves `review_id` **before** argparse
dispatch, bound to the original cwd. `open` therefore provisions, then
`os.execv(sys.executable, [python, abspath(argv[0]), "interactive", "-y"])` with cwd = worktree.
`main()` untouched; on re-entry `StateManager._get_git_dir` (`state.py:36-52`) puts state in
`.git/worktrees/pr-N/acre/`. Traps: take `abspath(argv[0])` **before** `chdir`; flush
stdout/stderr before `execv`.

### Provisioning: one gh call

`gh pr checkout <N> --worktree <abs-path> [--force]` (gh ≥ 2.102 verified). Verified in a
scratch clone of `octocat/Hello-World`:
- fork PR → fetches `refs/pull/N/head` onto a real local branch → `gh pr view` inside the
  worktree still infers the PR (`initialize.py:31` → `github.py:10` needs no change);
- rerun on an existing worktree → fetch + fast-forward, exit 0 (reopen = refresh);
- run from inside another worktree with an absolute path → works;
- PR's branch already checked out elsewhere (e.g. your own PR in the main checkout) → gh
  refuses. Surface its message; review your own PR in place.

Path is always absolute and anchored on the main checkout: `get_repo_root()` returns the
*current* worktree, so use `git worktree list --porcelain` (first `worktree ` line = main,
absolute; verified). `--git-common-dir` returns relative `.git` — unsuitable.

Path exists but isn't a registered worktree → error with `git worktree prune` hint.

### Teardown

`acre close [<pr-ref>] [--force]`; PR inferred from cwd path when omitted. `git worktree
remove` already refuses a dirty tree — surface its message, hint `--force`. `chdir(main_root)`
before removing; print `cd <main_root>` hint on stderr (parent shell is left in a deleted cwd).
Confirm prompt names the progress loss. Branch kept.

### Files

| File | Change |
|---|---|
| `src/lib/sources/git.py` | `_parse_worktree_list_porcelain`, `list_worktrees`, `get_main_worktree_root`, `worktree_remove`. |
| `src/lib/sources/github.py` | `pr_checkout_worktree(pr_number, path, *, force)`, `repo_name_with_owner()`. |
| `src/lib/worktree.py` *(new, pure)* | `parse_pr_ref`, `worktree_path_for_pr`, `pr_number_from_path`, `ensure_worktree_ignored`. |
| `src/lib/commands/worktree.py` *(new)* | `impl_open`, `impl_close`, `register` — shaped like `simple_commands.py:89-110`. |
| `src/lib/config/config.py` | `get_worktree_dir(config)`, `DEFAULT_WORKTREE_DIR = ".acre-worktrees"`, validate-or-fall-back like `get_diff_git_args` (`:41-49`). |
| `src/cli/parser.py` | register in `_build_argparse()`. Not in `interactive.py` → CLI-only. |
| `docs/config.example.toml` | `[worktree] dir` block. |

`init` untouched: `open` execs `interactive -y`, whose auto-init (`interactive.py:99-105`)
calls `cmd_init`.

### Thin `acre-start.sh`

Parses `<repo> <N>` | `owner/repo#N` | URL → `cd "${ACRE_REPOS_ROOT:-$HOME/code/reviews}/<repo>"`
→ `exec "$acre" open <pr-ref>`. Missing dir → error with a `gh repo clone` hint. Dirty
checks, default-branch checkout, `pull`, `init`, `overview` all go — `open` covers them or
they're no longer needed. Default root preserves today's layout.

### Commits

1. **`feat(worktree): resolve main checkout, worktree dir, PR refs`** — git.py resolvers,
   config accessor, `lib/worktree.py`, config docs. No user-visible surface.
2. **`feat: acre open <pr-ref> provisions a worktree`** — the payload.
3. **`feat: acre close removes a PR worktree`**.
4. *(after 1–3 merge to main)* **`enh: thin acre-start onto acre open`** + README command
   table, `git clean -xdf` caveat.

### Tests

| File | Covers |
|---|---|
| `test_worktree_main_root.py` | porcelain parse on a 3-worktree blob → main first. |
| `test_worktree_pr_ref.py` | all four ref forms; slug/URL repo mismatch → error; garbage → error. |
| `test_worktree_path.py` | `[worktree] dir` honored, garbage falls back; `pr_number_from_path` round-trip, `None` outside. |
| `test_worktree_exclude.py` | appends once, preserves contents, fixes missing trailing newline. |
| `test_worktree_open.py` | monkeypatched `subprocess.run`/`os.execv`: gh called with abs path + `cwd=main_root`, `--force` only when asked; gh failure → `SystemExit`, no exec. |
| `test_worktree_close.py` | chdir before remove; `--force` passthrough; inferred PR from cwd. |

**By hand:**
```sh
acre-next open <N>                  # interactive in .acre-worktrees/pr-N
git -C <main> status                # untouched
acre-next open <other-N>            # concurrent second PR
acre-next open <url>                # same as above via URL; foreign-repo URL → error
acre-next open <N>                  # reopen → ff refresh, state preserved
acre-next close <N>                 # confirm, cd hint
```

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

- Review progress dies with the worktree. Chosen — `acre close` then reopening starts over.
- `git clean -xdf` in the main checkout now deletes worktrees. README caveat only.
- `os.execv` breaks under a zipapp/PyInstaller build. Not in play (hatchling + a plain script).
- A PR whose branch is checked out elsewhere (your own PR in the main checkout) can't be
  opened in a worktree. Review it in place.

## Open

- None for Phase 1.
