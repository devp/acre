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

**Decided, not open:** worktrees at `<repo-root>/.acre-worktrees/pr-<N>`, configurable;
one real checkout per repo, no assumptions about surrounding dirs; review state stays
per-worktree and ephemeral (losing approvals on teardown is intended, so `state.py` is
untouched); skill ships in the acre repo.

---

## Phase 1 — `acre open <pr>` / `acre close`

### Key decision: re-exec, don't refactor startup

`src/codereview.py:19-28` builds `StateManager` and resolves `review_id` **before** argparse
dispatch, bound to the original cwd. A command that creates a worktree must then operate
inside it, and a subprocess can't cd its parent shell.

| Approach | Cost |
|---|---|
| **Re-exec `codereview.py` with cwd = new worktree** ← pick | ~4 lines. `main()` untouched; on re-entry `determine_review_id()` returns `branch-<pr-head>` and `StateManager._get_git_dir` (`state.py:36-52`, already written for this) puts state in `.git/worktrees/pr-N/acre/`. |
| Lazy `key`/`state_manager` on `Context` | Turns `cli/context.py` dataclass fields into properties — a shared interface every `impl_*` and `CommandsV0` consumes. 10-line feature becomes a 10-file diff. |
| Print path only + shell wrapper | Install friction; can't be the only path. Its consumer is served by a flag instead. |

**Serves both consumers from one command:** narration and git/gh output → stderr; the
absolute worktree path → stdout, always, one line.
- Human: `acre open 123` → provision → `os.execv` into `interactive -y`.
- Agent: `cd "$(acre open 123 --print-path)"` → `--print-path` suppresses only the exec.

Two silent-bug traps to encode: compute `os.path.abspath(sys.argv[0])` **before** `os.chdir`,
and flush stdout/stderr — `os.execv` does not.

### Mechanics

**Getting the PR in:** `git worktree add --detach <path>` from the main root, then
`gh pr checkout <N>` **inside** that worktree. Decisive reason is `init`:
`src/lib/initialize.py:31` calls `data_from_gh()`, which runs bare `gh pr view` and infers
the PR *from the current branch* (`github.py:10`). `gh pr checkout` leaves HEAD on a real
branch, so that inference keeps working with zero changes; a manual `refs/pull/N/head` fetch
leaves detached HEAD and would force a change to `data_from_gh`. `--detach` is load-bearing —
plain `worktree add` invents a branch named after the directory. Git's one-branch-one-worktree
rule becomes the double-provisioning guard for free.

**Anchoring to the one real checkout:** `get_repo_root()` returns the *current* worktree, so
`acre open` run from inside `pr-123` would nest `pr-456` in it. `git rev-parse --git-common-dir`
is unsuitable — verified, it returns the relative string `.git`. Use `git worktree list
--porcelain`; verified, the first `worktree ` line is the main worktree and is absolute.

**Ignoring the dir:** write `/<segment>/` to `.git/info/exclude`, not `.gitignore`.
`info/` lives in the common git dir so it covers every linked worktree, and it's untracked —
never dirties someone else's repo. README caveat: `git clean -xdf` in the main checkout now
deletes your worktrees.

**Dirty handling:** main-checkout dirty guards (`acre-start.sh:59-64`) are dropped entirely —
`worktree add` never touches the main tree. On close, don't reimplement: `git worktree remove`
already refuses a dirty tree; surface its message and hint `--force`. Path exists and is
registered → reuse silently (resuming a review is the common case). Exists but unregistered →
error with a `git worktree prune` hint.

**Teardown:** `acre close [<N>] [--force]`, PR inferred from cwd when omitted. Keep the local
branch (cheap; makes re-open instant). `os.chdir(main_root)` before removing so acre isn't
standing in the doomed dir, then print `main_root` on stdout and a `cd <main_root>` hint on
stderr — the parent shell is left in a deleted cwd otherwise. Name the progress loss in the
confirm prompt.

### Files

| File | Change |
|---|---|
| `src/lib/sources/git.py` | append `_parse_worktree_list_porcelain`, `list_worktrees`, `get_main_worktree_root`, `get_git_common_dir`, `worktree_add_detached`, `worktree_remove`. The last two deliberately don't capture output, matching `diff()` at `:110`. |
| `src/lib/sources/github.py` | append `pr_checkout(pr_number, *, cwd)` after `approve_pr` (`:52`). |
| `src/lib/worktree.py` *(new)* | pure: `worktree_path_for_pr`, `pr_number_from_path`, `ensure_worktree_ignored`. All inputs explicit. |
| `src/lib/commands/worktree.py` *(new)* | `impl_open`, `impl_close`, `register` — shaped like `simple_commands.py:89-110`. |
| `src/lib/config/config.py` | `get_worktree_dir(config)` + `DEFAULT_WORKTREE_DIR = ".acre-worktrees"`, matching the validate-or-fall-back shape of `get_diff_git_args` (`:41-49`). |
| `src/cli/parser.py` | one import by `:5-12`, one `register_worktree(sub)` in `_build_argparse()` (`:37-46`). Not registered in `interactive.py:19-36` → CLI-only, same as `unapprove`. |
| `docs/config.example.toml` | `[worktree] dir = ".acre-worktrees"` block. |

**Not on `init`:** `init`'s impl (`src/lib/commands/init.py:7-20`) operates on
`context.state_manager`, bound to the original git dir — provisioning there means `init`
re-execs itself, one verb with two contracts. Separate verbs leave `init.py` and
`initialize.py` at zero diff and compose anyway: `open` execs `interactive -y`, whose
auto-init at `interactive.py:99-105` calls `cmd_init`.

### Commits

1. **`feat(worktree): resolve main checkout and worktree dir`** — ~90 lines, no user-visible
   surface. git.py resolvers + config accessor + `lib/worktree.py` + config docs. Ships
   nothing, can't break anything.
2. **`feat: acre open <pr> provisions a worktree`** — ~90 lines. The payload; read this one
   carefully.
3. **`feat: acre close removes a PR worktree`** — ~60 lines, reuses all of the above.
4. **`doc: retire acre-start.sh in favor of acre open`** — delete
   `contrib/scripts/acre-start.sh` (every step is now covered), update `README.md:17-18`
   and the command table at `:21-43`, add an `acre-open` shell function to
   `docs/suggested-aliases.sh`, note the `git clean -xdf` caveat.
5. *(optional)* Port the URL/slug parsing from `acre-start.sh:14-28` so
   `acre open https://github.com/o/r/pull/123` and `acre open '#123'` work — ~6 lines + a test.

---

## Phase 2 — primitives + skill

Rule: **acre owns state and diff bytes; the model owns judgment.** No LLM call in acre, no
new dependency, no state schema change.

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

**New tests** (existing style: `src/tests/`, `monkeypatch`, `tmp_path`, driven through
`parse_args_from_cli(context=ctx, override_args=[...])`, asserting on `capsys`):

| File | Covers |
|---|---|
| `test_worktree_main_root.py` | `_parse_worktree_list_porcelain` on a 3-worktree blob → main first, `HEAD`/`branch`/`detached` lines ignored. Pure. |
| `test_worktree_path.py` | `worktree_path_for_pr` honors `[worktree] dir`, falls back on garbage config; `pr_number_from_path` round-trip + `None` outside the dir. |
| `test_worktree_provision.py` | monkeypatched `subprocess.run`: ordered `git worktree add --detach` with `cwd=main_root` then `gh pr checkout` with `cwd=path`; `gh` raising → `worktree remove --force` + `SystemExit`. |
| `test_worktree_exclude.py` | `ensure_worktree_ignored` appends once, preserves contents, fixes a missing trailing newline, no-ops on second call. |
| `test_state_view.py` | indices 1-based and in `ls` order; the `total == 0` percent branch. |
| `test_status_json.py` | `json.loads(out)` parses and `"\x1b" not in out`; non-`--json` still prints the bar (guards the `cmd_status` restructure). |
| `test_review_no_prompt.py` | `mark_reviewed_prompt` and `review.yn` monkeypatched to raise — neither is reached. |
| `test_mark_reviewed_command.py` | by path, by index, multiple items, unknown file → `SystemExit` + message on **`.err`**, absent from the interactive parser (mirrors `test_unapprove_command.py:125-131`). |
| `test_color_enabled.py` | non-tty false, `NO_COLOR` false, `CLICOLOR_FORCE` true — via injected `stream=`/`env=`. |

**Existing tests that change behavior** (flag in review, not churn):
`test_unapprove_command.py:121-122` stdout → stderr; `test_git_diff_lines_color.py:27,54`
pass `color=True`, plus a new case asserting `--no-color` present / `--color=always` absent /
`shutil.which` never consulted.

**End-to-end, by hand:**
```sh
acre open <pr>                      # lands in interactive, worktree at .acre-worktrees/pr-N
git -C ~/code/<repo> status         # main checkout clean and untouched
acre open <other-pr>                # second PR, same repo, concurrent — the thing that was impossible
cd "$(acre open <pr> --print-path)" # agent path: one line on stdout, exit 0
acre status --json | jq .progress
acre review --no-prompt 3 | head    # no hang, no ANSI through the pipe
acre mark-reviewed 3 && acre status --json | jq '.files[2].reviewed'
acre review nonexistent.py; echo $? # 1, message on stderr
acre close <pr>                     # confirms progress loss, cd hint on stderr
```
Test one **fork** PR before finalizing — `gh pr checkout` in a linked worktree resolves the
repo from `git remote -v` (shared across worktrees), so it should hold, but confirm it.

---

## Costs, stated

- Review progress dies with the worktree. Chosen — `acre close` then reopening starts over.
- `git clean -xdf` in the main checkout now deletes worktrees. README caveat only.
- `os.execv` breaks under a zipapp/PyInstaller build. Not in play (hatchling + a plain script).
- The skill lives in acre, diverging from your `~/code/prompts/` convention. The symlink makes
  it behave identically; the win is it can't drift from the CLI it documents.

## Open

- Delete `contrib/scripts/acre-start.sh` outright, or keep it as a thin shim? Plan assumes
  delete, with its URL/slug parsing optionally ported into `open`.
