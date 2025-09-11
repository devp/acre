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
                     {init,status,ls,overview,reset,review,interactive} ...

positional arguments:
  {init,status,ls,overview,reset,review,interactive}
    init                Initialize a new code review session
    status              Status of review
    ls                  List of files for this review, including their
                        numbered indexes
    reset               Reset the progress of the code review
    interactive         Starts an interactive session

options:
  -h, --help            show this help message and exit
```

Custom aliases are encouraged for the script (see `./docs/suggested-aliases.sh`)

## Requirements

- Python 3.x
- `git`
- `gh`
+ for development:
    - justfile (to run tasks; or you can read the file and run them yourself)
    - poetry (only to run the tasks above; currently, no dependencies for the script itself)

## Roadmap

=> `./docs/development/todo.md`

## Notes

### Why `acre`?

- TODO: write about my code review philosophy and workflow
- See also `./docs/development/spec.md` for my initial spec, which captures some of my goals.

### What does `acre` stand for?

One of:

* a code review engine
* augmented code review excellence
* agentic code review executor *(not really agentic)*
* awesome code review e-ssistant *(really?)*
* acre = ACRE Code Review via ECRA *(wow.)*
  * ECRA = enhanced command-line routine for ACRE *(WOW.)*
