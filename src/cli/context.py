from dataclasses import dataclass

from lib.state import StateManager


@dataclass
class Context:
    key: str
    state_manager: StateManager
    config: dict
