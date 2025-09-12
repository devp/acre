alias acre=codereview

# Create your own aliases for custom workflows.
alias acre-pr-number="acre metadata | jq -r .pr_number"
alias acre-tests-all='for x in `acre ls --raw | rg "/test_"`; do echo $x; rg "class Test|def test_" $x; done'
alias acre-tests-diff='for x in `acre ls --raw | rg "/test_"`; do echo $x; git diff `acre metadata | jq -r .base_commit` -- $x | rg "class Test|def test_"; done'
