import json
from traceback import format_exc
from typing import Optional, Dict, List, Any
from nearai.agents.environment import Environment
from pydantic import BaseModel
from litellm import Message


class PendingSecrets(BaseModel):
    use_secrets: bool = False
    keys: Optional[Dict[str, str]]
    values: Optional[Dict[str, str]] = None


class AgentState(BaseModel):
    metadata: str       = ""
    agent_py: str       = ""
    agent_name: str     = ""
    agent_description: str = ""
    last_version: str   = ""
    pending_secrets: Optional[PendingSecrets] = None
    scratchpad: str     = ""


class Context:
    _instance: Optional["Context"] = None
    _state: AgentState = None

    def __new__(cls, env: Environment = None):
        if cls._instance is None:
            assert env is not None
            cls._instance = super().__new__(cls)
            cls._instance.env = env  # Initialize env only once
            cls._instance._state = AgentState()
        return cls._instance

    def load_state(self):
        try:
            filename = f"{Context().env.get_thread().id}_state.json"

            state_json = self.env.read_file(filename)
            if state_json is None:
                state = AgentState()
            else:
                state = AgentState.model_validate_json(state_json)
                self.env.add_system_log(f"Successfully loaded {filename}")
            self._state = state
        except Exception as e:
            self._state = AgentState()
            self.env.add_system_log(f"Cannot load {filename}, error:\n{format_exc()}")

    def dump_state(self):
        filename = f"{Context().env.get_thread().id}_state.json"
        try:
            self.env.write_file(filename, self._state.model_dump_json())
        except Exception as e:
            self.env.add_system_log(f"Cannot save {filename}, error:\n{format_exc()}")

    def write_message_to_scratchpad(self, message: Any):
        if isinstance(message, str):
            text = message
        elif isinstance(message, Message):
            text = message.model_dump_json()
        else:
            try:
                text = json.dumps(message)
            except Exception as e:
                text = str(message)

        if text is not None:
            self.state.scratchpad += f"\n{text}"
            self.env.add_system_log(f"+++++++\nWriting to scratchpad:\n{text}\n+++++++")

    @property
    def state(self) -> AgentState:
        return self._state