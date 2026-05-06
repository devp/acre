# Bash completion for acre
#
# Setup (choose one):
#   1. Source in ~/.bashrc:
#        source ~/code/misc/acre/contrib/completions/acre.bash
#
#   2. Copy to bash-completion drop-in dir:
#        cp ~/code/misc/acre/contrib/completions/acre.bash \
#           /usr/local/share/bash-completion/completions/acre
#        # or: ~/.local/share/bash-completion/completions/acre

_acre() {
  local cur prev words cword
  if declare -f _init_completion &>/dev/null; then
    _init_completion 2>/dev/null
  else
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    words=("${COMP_WORDS[@]}")
    cword=$COMP_CWORD
  fi

  local cmds="init status ls overview reset metadata approve aliases webpeek review preapprove interactive help h"

  # Completing the subcommand
  if [[ $cword -eq 1 ]]; then
    COMPREPLY=($(compgen -W "$cmds" -- "$cur"))
    return
  fi

  local subcmd="${words[1]}"

  # Completing subcommand arguments
  case "$subcmd" in
    init)
      case "$prev" in
        --review-id|--git-range)
          # free-form value, no completion
          return ;;
      esac
      COMPREPLY=($(compgen -W "--review-id --force --git-range" -- "$cur"))
      ;;

    ls)
      COMPREPLY=($(compgen -W "--todo --raw" -- "$cur"))
      ;;

    reset)
      COMPREPLY=($(compgen -W "--destroy" -- "$cur"))
      ;;

    review)
      if [[ "$cur" != -* ]]; then
        # numeric index or file path
        COMPREPLY=($(compgen -f -- "$cur"))
      else
        COMPREPLY=($(compgen -W "
          --todo
          --skim
          --loc-lte
          --test-diff-first
          --focus-regex
          --regex-include-context
          --diff-line-numbers
          --hunk-numbers
        " -- "$cur"))
      fi
      ;;

    preapprove)
      if [[ $cword -eq 2 && "$cur" != -* ]]; then
        # first positional: file or index
        COMPREPLY=($(compgen -f -- "$cur"))
      elif [[ $cword -eq 3 && "$cur" != -* ]]; then
        # second positional: hunk/range — no meaningful completion
        return
      else
        COMPREPLY=($(compgen -W "--notes --clear" -- "$cur"))
      fi
      ;;

    webpeek)
      if [[ $cword -eq 2 ]]; then
        COMPREPLY=($(compgen -f -- "$cur"))
      fi
      ;;

    interactive)
      COMPREPLY=($(compgen -W "-y --auto-yes" -- "$cur"))
      ;;
  esac
}

complete -F _acre acre
