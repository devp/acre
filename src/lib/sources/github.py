from dataclasses import dataclass, field
import json
import sys
import subprocess
from typing import List, Optional

@dataclass
class GHData:
    title: Optional[str] = None
    body: Optional[str] = None
    number: Optional[int] = None
    files: List[str] = field(default_factory=list)
    lines_changed: dict[str, int] = field(default_factory=dict)


def data_from_gh():
    try:
        res = subprocess.run(
            ["gh", "pr", "view", "--json", "title,body,files,number"],
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
        )
    except subprocess.CalledProcessError:
        print("gh pr view failed; ensure you're on a PR branch")
        print("TODO: make this robust for other branches and other info sources")
        sys.exit(1)
