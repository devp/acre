# acre

**acre** is a code review engine: a personal tool for tracking and managing code review progress.

## Features

- Track review progress across multiple files
- Interactive review mode with command shortcuts
- GitHub integration for pull request reviews
- Configurable aliases and default commands (see `./docs/config.example.toml`)
- State persistence in `.git/acre/` directory
- Includes context from Github (and optionally Jira)
- a responsibly modest amount of whimsy

## Usage

Run the `codereview.py` script from the base directory of your git repo, at a branch that
is related to a Github PR (i.e. `gh pr checkout`).

```
usage: codereview.py [-h]
                     {init,status,ls,overview,reset,metadata,approve,webpeek,review,preapprove,unapprove,interactive} ...

positional arguments:
  {init,status,ls,overview,reset,metadata,approve,webpeek,review,preapprove,unapprove,interactive}
    init                Initialize a new code review session
    status              Status of review
    ls                  List of files for this review, including their
                        numbered indexes
    reset               Reset the progress of the code review
    metadata            Get metadata from review state, output as JSON
    approve             Approve the current PR after confirmation
    overview            Print PR summary, Jira link, file list, and status
    webpeek             Open a file in the GitHub PR diff view (e.g. for comments)
    review              Review one or more files
    preapprove          Mark diff line ranges as pre-approved, hiding them
                        from future review diffs
    unapprove           Revert one or more files back to unreviewed
    interactive         Starts an interactive session

options:
  -h, --help            show this help message and exit
```

### Preapproval workflow

`preapprove` lets you hide diff ranges you've already processed (e.g. generated code, noise, boilerplate) so subsequent `review` runs show only what remains. Files with active preapprovals show a `[N PA]` count in `ls` output.

```bash
# See diff line numbers (dim grey) and hunk labels to identify what to hide
acre review 3 --diff-line-numbers --hunk-numbers

# Hide a whole hunk by number (plain integer or H-prefixed)
acre preapprove 3 2        # hides hunk 2 of file #3
acre preapprove 3 H02      # same thing

# Hide a line range
acre preapprove 3 12:18 --notes "generated types"

# Open-ended ranges
acre preapprove 3 :10      # lines 1–10
acre preapprove 3 25:      # line 25 through end of diff

# Focus a review on hunks matching a pattern
acre review 3 --focus-regex "async def"

# Clear all pre-approvals for a file
acre preapprove 3 --clear
```

Pre-approved line numbers refer to the 1-based position in the rendered diff output (as shown by `--diff-line-numbers`), **not** source-file line numbers. Numbers stay stable across multiple `preapprove` calls on the same file.

**Inline preapproval during review:** at the mark-reviewed prompt, type `p <hunk|range>` to preapprove without leaving the review flow:

```
Mark reviewed? [y/N/e/w/p <hunk|range>] p 2
Preapproved hunk 2 (lines 7-14) of src/api.py
Mark reviewed? [y/N/e/w/p <hunk|range>] p 40:55
Preapproved lines 40-55 of src/api.py
Mark reviewed? [y/N/e/w/p <hunk|range>] y
```

### Unapproving a file

`unapprove` reverts one or more already-reviewed files back to unreviewed, by path or by index from `ls`. It's CLI-only (not exposed in `interactive`), and requires at least one file/index argument.

```bash
acre unapprove src/api.py     # by path
acre unapprove 3              # by index from `ls`
acre unapprove 3 5 src/api.py # multiple at once
```

Custom aliases are encouraged for the script (see `./docs/suggested-aliases.sh`)

## Requirements

- Python 3.x
- `git`
- `gh`
+ for development:
    - justfile (to run tasks; or you can read the file and run them yourself)
    - uv (to run the tasks; `uv sync --dev`, then `just test`)

## Notes

### Why `acre`?

tl;dr - this is the tool I've wished for based on my mental model for good code review.

### What does `acre` stand for?

One of:

* a code review engine
* augmented code review excellence
* agentic code review executor *(not really agentic)*
* awesome code review e-ssistant *(really?)*
* acre = ACRE Code Review via ECRA *(wow.)*
  * ECRA = enhanced command-line routine for ACRE *(WOW.)*

## Roadmap / TODOs

- `1.0`: a version I'm confident that others can use
    - [ ] enh: autocomplete for cli
    - [ ] doc: explain my code review philosophy (and give context to this script)
    - [ ] doc: quickstart

## Credits

Thanks to my lovely spouse, @labmouse, for encouraging me to follow my inspirations
(and for laughing with me at my corny programming jokes).
