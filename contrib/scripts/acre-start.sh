set -e

# Resolve the acre CLI: prefer one on PATH, else $ACRE, else the local checkout.
if command -v acre >/dev/null 2>&1; then
  acre=acre
else
  acre="${ACRE:-$HOME/code/misc/acre/src/codereview.py}"
  [[ -x "$acre" ]] || { echo "acre CLI not found; set \$ACRE or symlink it onto PATH" >&2; exit 1; }
fi

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

reviews_dir="$HOME/code/reviews"
repo_dir="$reviews_dir/$repo"

confirm() {
  local reply
  read -r -p "$1 [y/N] " reply
  [[ "$reply" == [yY] || "$reply" == [yY][eE][sS] ]]
}

if [[ ! -d "$reviews_dir" ]]; then
  confirm "Reviews dir $reviews_dir missing. Create it?" || { echo "Aborting: no reviews dir." >&2; exit 1; }
  mkdir -p "$reviews_dir"
fi

if [[ ! -d "$repo_dir" ]]; then
  confirm "Repo dir $repo_dir missing. Clone it now?" || { echo "Aborting: no repo dir." >&2; exit 1; }
  read -r -p "Clone source (owner/repo or URL): " clone_src
  [[ -n "$clone_src" ]] || { echo "Aborting: no clone source." >&2; exit 1; }
  gh repo clone "$clone_src" "$repo_dir"
fi

cd "$repo_dir" || exit 1
git diff --cached --exit-code -s
git diff --exit-code -s
git checkout main
git pull --ff-only -q
gh pr dco $pr
"$acre" init
"$acre" overview
"$acre" interactive
