from cli.pretty import print_whimsically
from cli.util import ynxyz
from lib.sources.git import diff
from lib.sources.github import data_from_gh
from lib.sources.jira import find_jira_tag
from lib.state import StateManager



class CommandsV0:
    """Simple earlier versions of some commands."""

    def __init__(self, state_manager: StateManager, key: str, config={}):
        self.key = key
        self.config = config
        self.state_manager = state_manager
        _state = self.state_manager.load_state(key)
        if not _state:
            print("No state file: run init first")
            exit(1)
        self.state = _state

    def cmd_overview(self):
        data = data_from_gh()
        title = data.title or ""
        body = data.body or ""
        print(f"\U0001F4CC PR Summary: {title}")
        jira = find_jira_tag(data)
        jira_base = self.config.get("jira", {}).get("base")
        if data.number:
            print(f"Ticket: #{data.number}")
        if jira and jira_base:
            print(f"\U0001F517 Jira: https://{jira_base}.atlassian.net/browse/{jira}")
        elif jira:
            print(f"\U0001F517 Jira: {jira}")
        if body:
            print(f"> {body}")
        self.cmd_list_files()
        self.cmd_status()

    def cmd_list_files(self, todo_only=False, raw=False):
        if not raw:
            print("\n\U0001F4C1 File Summary:")
        for idx, path in enumerate(self.state.files, 1):
            reviewed = self.state.is_file_reviewed(path)
            if todo_only and reviewed:
                continue
            if raw:
                print(path)
                continue
            file = self.state.files.get(path)
            lines = file.lines if file else 0
            mark = "\u2705 " if reviewed else ""
            print(f"{idx}. {mark}{path:25} Δ{lines}")

    def cmd_status(self):
        total = self.state.total_lines()
        reviewed = self.state.total_reviewed_lines()
        remaining = total - reviewed
        pct = int((reviewed / total) * 100) if total else (100 if reviewed else 0)
        num_files = len(self.state.files)
        num_files_reviewed = len(self.state.reviewed_files())
        files_left = num_files - num_files_reviewed
        text = f"> {remaining} lines remaining | {pct}% reviewed | {files_left} files touched"
        if files_left == 0 and num_files > 0:
            print_whimsically(text)
        else:
            print(text)

    def cmd_review(self, path, mode="default", ask_approve=True):
        """Reviews a single file"""
        if self.state.is_file_reviewed(path):
            print(f"{path} already reviewed")
            return False
        diff(path, diff_target=self.state.diff_target())
        if not ask_approve:
            return
        
        while True:
            response, raw_input = ynxyz("Mark reviewed? ([c]opy filename, [e]dit file)")
            
            if response is True:
                # User said yes
                break
            elif response is False:
                # User said no
                return
            else:
                # Handle other commands
                command = raw_input.lower()
                if command == "c" or command == "copy":
                    print("Not implemented")
                    continue
                elif command == "e" or command == "edit":
                    print("Not implemented") 
                    continue
                else:
                    print(f"Unknown command: {raw_input}")
                    continue
        
        self.state_manager.mark_file_reviewed(self.state, path)
        self.state_manager.save_state(self.state)
        lines = self.state.lines_of_file(path)
        print(f"> Marked {lines} lines as reviewed ({mode} mode)")

    def cmd_reset(self):
        self.state_manager.do_reset(self.state)
        self.state_manager.save_state(self.state)
