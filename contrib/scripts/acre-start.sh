alias acre=~/code/misc/acre/src/codereview.py

set -e

repo="$1"
pr="$2"

# Support gh slug form: owner/repo#123
if [[ $# -eq 1 && "$1" == */*#* ]]; then
  repo="${1#*/}"
  repo="${repo%%#*}"
  pr="${1##*#}"
fi

# Support GitHub PR URL form:
# https://github.com/owner/repo/pull/123
if [[ $# -eq 1 && "$1" == https://github.com/*/*/pull/* ]]; then
  repo="${1#https://github.com/}"
  repo="${repo#*/}"
  repo="${repo%%/pull/*}"
  pr="${1##*/}"
fi

if [[ -z "$repo" || -z "$pr" ]]; then
  echo "Usage: acre-start <code-review-subdir> <gh-pr-number>"
  exit 1
fi

echo "acre-start => repo $repo @ PR #$pr"
cd "$HOME/code/reviews/$repo" || exit 1
git diff --cached --exit-code -s
git diff --exit-code -s
git checkout main
git pull --ff-only -q
gh pr dco $pr
acre init
acre overview
acre interactive
