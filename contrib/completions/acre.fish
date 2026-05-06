# Fish completion for acre
#
# Setup:
#   ln -s ~/code/misc/acre/contrib/completions/acre.fish \
#         ~/.config/fish/completions/acre.fish

# Disable file completion by default
complete -c acre -f

# Subcommands
complete -c acre -n '__fish_use_subcommand' -a init        -d 'Initialize a new code review session'
complete -c acre -n '__fish_use_subcommand' -a status      -d 'Status of review'
complete -c acre -n '__fish_use_subcommand' -a ls          -d 'List files for this review with numbered indexes'
complete -c acre -n '__fish_use_subcommand' -a overview    -d 'Print overview of review context'
complete -c acre -n '__fish_use_subcommand' -a reset       -d 'Reset the progress of the code review'
complete -c acre -n '__fish_use_subcommand' -a metadata    -d 'Get metadata from review state as JSON'
complete -c acre -n '__fish_use_subcommand' -a approve     -d 'Approve the current PR after confirmation'
complete -c acre -n '__fish_use_subcommand' -a aliases     -d 'List all configured aliases'
complete -c acre -n '__fish_use_subcommand' -a webpeek     -d 'Open a changed file in the GitHub PR diff view'
complete -c acre -n '__fish_use_subcommand' -a review      -d 'Review one or more files'
complete -c acre -n '__fish_use_subcommand' -a preapprove  -d 'Mark diff hunks or line ranges as pre-approved'
complete -c acre -n '__fish_use_subcommand' -a interactive -d 'Start an interactive review session'
complete -c acre -n '__fish_use_subcommand' -a help        -d 'Show help'

# init flags
complete -c acre -n '__fish_seen_subcommand_from init' -l review-id       -d 'Custom review identifier' -r
complete -c acre -n '__fish_seen_subcommand_from init' -l force            -d 'Overwrite existing state file'
complete -c acre -n '__fish_seen_subcommand_from init' -l git-range        -d 'Git range for diff (e.g. main..HEAD)' -r

# ls flags
complete -c acre -n '__fish_seen_subcommand_from ls' -l todo -d 'Only list unreviewed files'
complete -c acre -n '__fish_seen_subcommand_from ls' -l raw  -d 'Output raw filenames only'

# reset flags
complete -c acre -n '__fish_seen_subcommand_from reset' -l destroy -d 'Delete the state file entirely'

# review flags
complete -c acre -n '__fish_seen_subcommand_from review' -l todo                   -d 'Only review unreviewed files'
complete -c acre -n '__fish_seen_subcommand_from review' -l skim                   -d 'Show all diffs and ask for approval as a whole'
complete -c acre -n '__fish_seen_subcommand_from review' -l loc-lte                -d 'Only review files with lines changed <= N' -r
complete -c acre -n '__fish_seen_subcommand_from review' -l test-diff-first        -d 'Show test diff subset before full diff'
complete -c acre -n '__fish_seen_subcommand_from review' -l focus-regex            -d 'Only show hunks where a changed line matches regex' -r
complete -c acre -n '__fish_seen_subcommand_from review' -l regex-include-context  -d 'Also match context lines with --focus-regex'
complete -c acre -n '__fish_seen_subcommand_from review' -l diff-line-numbers      -d 'Prefix each diff line with its 1-based line number'
complete -c acre -n '__fish_seen_subcommand_from review' -l hunk-numbers           -d 'Annotate each hunk header with a 1-based hunk number'

# preapprove flags
complete -c acre -n '__fish_seen_subcommand_from preapprove' -l notes -d 'Notes about why this range is pre-approved' -r
complete -c acre -n '__fish_seen_subcommand_from preapprove' -l clear -d 'Clear all preapproved blocks for this file'

# interactive flags
complete -c acre -n '__fish_seen_subcommand_from interactive' -s y -l auto-yes -d 'Automatically answer yes to initialization prompts'
