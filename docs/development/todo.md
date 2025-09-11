# Roadmap

- `0.9`: a version I'm using daily and finding useful
- `1.0`: a version I'm confident that others can use

# Enhancements

- save PR number to metadata
- add command to get data from the review state with dot operators, mainly a convenience for getting PR number for gh usage
- The review command should accept a flag `--skim` , which emits the diffs for
  the chosen files at aonce, and asks a single yb approve to approve or not approve-all.
- The review command should accept a flag `--loc-lte <int>`, which selects files
  where the `lines` changed is <= the <int>.
- The ls command accepts a flag `--raw` that just emits the raw filenames separated by linebreaks
  with no other information. This is useful for custom pipe commands,
  e.g. `acre ls --todo --raw | xargs cat | rg "class Test|def test"` to summarize tests.

# Features

- interactive history (readline? I basically want the up arrow to work like I expect.)
- autocomplete for cli (argcomplete library?)
- options for: custom bases, custom ranges, over commits, without tickets or without GH
- notes and annotations by file
- notes and annotations by block/line
- line-by-line deep dives & approvals
- filter-by-regex for review and approve line-by-line over one or all files
- semantic grouping
- see also: `./spec.md`

# Chores

- python version: determine how low a version of 3.x can be supported
- I find your lack of tests distrubing. `:-/`
