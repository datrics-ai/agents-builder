import logging
from datetime import datetime
from utils import Context
from prompts import regenerate_code_prompt
from tools.upload import upload
from traceback import format_exc


def update_agent(update_plan: str):
    """Update a new NEAR AI agent and upload a test version to NEAR AI Hub.

    update_plan (str with markdown-formatted list): A list of improvements to the exiting code of the agent, it can be bugs, or additional features to implement. Note that you can only use a limited subset of packages, so try to use only basic stuff, since it's only for prototyping."""

    env = Context().env
    try:
        env.add_system_log(f"So, I'm gonna update the code, the plan is:\n{update_plan}")

        agent_py = Context().state.agent_py
        if agent_py is None or agent_py == "":
            env.add_system_log("Agent was not created yet or was not saved")

        # env.add_system_log(f"Current code of the agent is: \n```python\n{agent_py}```")

        conversation = []
        conversation.append({
            'role': 'system',
            'content': regenerate_code_prompt(agent_py, update_plan)
        })

        agent_py = env.completion(conversation)
        agent_py = agent_py.strip("```python").strip("```")

        env.add_reply(f"I have generated the updated code for you: \n```python\n{agent_py}```")

        env.add_system_log("Writing updated metadata.json...")
        env.write_file("metadata.json", Context().state.metadata)

        env.add_system_log("Writing updated agent.py...")
        env.write_file("agent.py", agent_py)

        Context().state.agent_py = agent_py

        env.add_system_log("Agent updated successfully.")
        upload(f"gen-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    except Exception as e:
        env.add_system_log(f"Error when updating agent, error:\n{format_exc()}", logging.DEBUG)
        return {"error": f"Error when updating agent, error: \n{format_exc()}"}