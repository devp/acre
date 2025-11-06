import json
import subprocess

from lib.sources.git import GitData, get_name_rev

GHData = GitData

def data_from_gh(retry_remote_branch=False):
    try:
        cmds = ["gh", "pr", "view", "--json", "title,body,files,number,baseRefOid,headRefOid"]
        if retry_remote_branch:
            name_rev = get_name_rev()
            if name_rev.startswith("remotes/origin/"):
                name_rev = name_rev.replace("remotes/origin/", "")
            cmds.append(name_rev)
        res = subprocess.run(
            cmds,
            check=True,
            capture_output=True,
            text=True,
        )
        data = json.loads(res.stdout)
        files = [
            f.get("path")
            for f in data.get("files", [])
            if f.get("path")
        ]
        lines_changed = {
            f.get("path"): (f.get("additions", 0) + f.get("deletions", 0))
            for f in data.get("files", [])
            if f.get("path")
        }
        number = int(data.get("number")) if data.get("number") else None
        return GHData(
            title=data.get("title"),
            body=data.get("body"),
            number=number,
            files=files,
            lines_changed=lines_changed,
            base_commit=data.get("baseRefOid"),
            head_commit=data.get("headRefOid"),
        )
    except subprocess.CalledProcessError:
        if not retry_remote_branch:
            return data_from_gh(retry_remote_branch=True)
        else:
            print("No GH data found for branch")
            return GHData()
