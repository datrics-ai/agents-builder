import logging
from datetime import datetime

from utils import Context, PendingSecrets
from prompts import generate_code_prompt
from traceback import print_exc, format_stack, format_exc
from tools.upload import upload
import json


def create_metadata(agent_name: str, agent_description: str):
    env = Context().env
    env.add_system_log("Writing metadata.json...")
    metadata_json = json.dumps({
        "name": agent_name,
        "version": "",
        "description": agent_description,
        "category": "agent",
        "tags": ["generated"],
        "details": {
            "agent": {
                "defaults": {
                    "model": "deepseek-3",
                    "inference_framework": "nearai"
                },
                "framework": "web-agent"
            }
        },
        "show_entry": True
    }, indent=2)
    env.write_file("metadata.json", metadata_json)


def _generate_agent_code(conversation:list, agent_technical_plan: str, use_mock: bool = False):

    env = Context().env

    env.add_system_log("Generating agent.py...")

    conversation.append({
        'role': 'system',
        'content': generate_code_prompt(agent_technical_plan)
    })

    if use_mock:
        with open("agent_py", "r") as f:
            agent_py = f.read()
    else:
        agent_py = env.completion(conversation)
        agent_py = agent_py.strip("```python").strip("```")

        conversation.append({"role": "assistant", "content": agent_py})
        agent_py = env.completion(conversation + [{
            "role": "user",
            "content": f"""
Make sure the code follows these guidelines and best practices:
- If you get JSON data, a good pattern is to process the JSON data using another LLM call using `env.completion([messages])` and then display this human-readable result to the user.
- If you use third-party APIs, you can use APIs which require API Key for authentication, but use those only if user directly asked for using the specific api
- Use only framework-provided methods for file I/O, or libraries that are supported by the framework.
- You MUST ALWAYS add a docstring to functions that are used as tools. Methods without a docstring don't work.
- Don't try to use messages from `env.list_messages()` directly as input to tools, since they are always human-readable instructions, not exact input. For tools, use tool registry.
- Don't use asyncio in any case!

Respond with the improved code only, nothing else, no comments, no formatting.
            """
        }])
        agent_py = agent_py.strip("```python").strip("```")
        conversation.pop()

    conversation.append({"role": "assistant", "content": agent_py})
    env.add_reply(f"I have generated code for you: \n```python\n{agent_py}```")
    return agent_py


def _check_if_code_has_authentication(agent_py: str):

    message = Context().env.completion([
        {
            "role": "system",
            "content": "Check if the code has any API key placeholders, "
                       "or uses APIs that require auth but don't have it supplied in the code. "
                       "Reply with json with format:"
                       "<response_format>"
                       "{ "
                       "     \"use_secrets\": true, # if code uses env variables or not" 
                       "     \"keys\": { "
                       "         \"key_1\": \"Description on why this key is needed\", "
                       "         \"key_2\": \"Description on why this key is needed\"  "
                       "     } "
                       "} "
                       "</response_format>"
                       "Reply only with json"

        },
        {"role": "user", "content": agent_py}
    ])

    Context().env.add_system_log("Figured out if agent uses private APIs \n" + message)

    try:
        result = json.loads(message.strip("```json").strip("```"))
        pending_secrets = PendingSecrets.model_validate(result)
        return pending_secrets
    except Exception as e:
        Context().env.add_system_log(f"Cannot figure out what env variables are used, skipping this step. Error:\n{format_exc()}")
    return PendingSecrets().model_validate({
        "use_secrets": False,
        "keys": [],
        "values": []
    })

def _provide_instructions_on_authentication(secrets: PendingSecrets, agent_py: str):
    env = Context().env
    message = env.completion([
        {
            "role": "system",
            "content": "Write message to the user that he should provide you with the API Key and give him the format and instructions of how he should provide this key."
                       "Do not provide any code snippets, only instructions on how to get API Key from the website."
                       "<examples>"
                       "    <example>"
                       "        To use the CoinMarketCap API, you will need to provide an API key. Here’s how you can provide the API key and format it correctly"
                       "        ### Instructions:"
                       "            1. **Obtain an API Key**: Sign up on the [CoinMarketCap API website](https://pro.coinmarketcap.com/signup) and create a new API key."
                       "            2. **Provide the API Key**: Once you have the API key, you can add it to the 'Environment Variables' list on the right panel of NEAR Hub. Or you can message it to me and I will store it for you."
                       "    </example>"
                       "</examples>"
        },
        {"role": "user", "content": "Code of the agent: \n" + agent_py},
        {"role": "user", "content": "List of environment variables or secrets that user should provide \n" + secrets.model_dump_json()}
    ])
    env.add_reply(message)


# TODO: this method would generate the template to save secrets
# Don't use as for now
def _generate_secrets_form(agent_py: str):
    env = Context().env
    message = env.completion([
        {
            "role": "system",
            "content": "Identify all environment variables accessed in the provided source code."
                        "Environment variables are accessed via env.env_vars."
                        "Return a JSON list of the accessed environment variables."
                        "Return JSON only"
        },
        {"role": "user", "content": agent_py}
    ])

    try:
        secrets = json.loads(message.strip("```json").strip("```"))

    except Exception as e:
        Context().env.add_system_log(f"Cannot identify environment variables in the code. Error:\n{format_exc()}")

def generate(agent_name: str, agent_description: str, agent_technical_plan: str):
    """Generate a new NEAR AI agent and upload a test version to NEAR AI Hub.

    agent_name (str): The name of the agent. Should match ^[a-zA-Z0-9_\\-.]+$
    agent_description (str): A short description of the agent.
    agent_technical_plan (str with markdown-formatted list): A list of technical capabilities the agent has, this will be a technical description of the agent passed to the developer to implement. This is a technical plan of what steps to take in the code, what APIs to use, what data to fetch, etc. Note that you can only use a limited subset of packages, so try to use only basic stuff, since it's only for prototyping."""

    context = Context()
    context.state.agent_name = agent_name
    context.state.agent_description = agent_description
    env = context.env

    env.add_system_log("Generating agent...")
    try:
        create_metadata(agent_name, agent_description)
        conversation = []
        agent_py = _generate_agent_code(conversation, agent_technical_plan)
        secrets = _check_if_code_has_authentication(agent_py)
        if secrets.use_secrets:
            Context().state.pending_secrets = secrets
            _provide_instructions_on_authentication(secrets, agent_py)

        env.write_file("agent.py", agent_py)
        env.add_system_log("Agent generated successfully.")

        version = f"gen-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        Context().state.last_version = version
        Context().state.agent_py = agent_py
        Context().dump_state()

        upload(version)
    except Exception as e:
        env.add_system_log(str(e))
        return {"error": print_exc()}
    finally:
        env.mark_done()