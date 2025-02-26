import os
import nearai
import json
import logging
from traceback import format_exc
from nearai.agents.environment import Environment


env: Environment = globals()["env"]


try:
    from prompts import scratchpad_prompt
    from utils import Context
    from tools import generate, upload, update_agent, create_secret, start_login_flow, finish_login_flow

    if os.environ.get("DEBUG", False):
        logger = logging.getLogger("system_logger")
        logger.setLevel(logging.DEBUG)

        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                logger.removeHandler(handler)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        logger.addHandler(console_handler)


    context = Context(env)
    context.load_state()


    def run(env: Environment):
        try:
            config = env.env_vars.get("NEARAI_CONFIG", None)

            if config is not None:
                config = json.loads(config)
                nearai.CONFIG = nearai.CONFIG.update_with({"auth": config})
            else:
                env.add_system_log("Cannot update nearai.CONFIG, no environ set. Loging in", logging.DEBUG)

        except Exception as e:
            env.add_system_log("Cannot update nearai.CONFIG, no environ set", logging.DEBUG)
            env.add_reply(f"Error when loging in:\n{format_exc()}")

        if context.state is not None:
            context.env.add_system_log(f"State: {context.state.model_dump_json()}")
        else:
            context.env.add_system_log(f"State is empty")

        if context.env.get_last_message()["content"].find("nearai login save") == 0:
            finish_login_flow(context.env.get_last_message()["content"])
            context.env.mark_done()
            return

        try:
            tool_registry = env.get_tool_registry(new=True)
            tool_registry.register_tool(generate)
            tool_registry.register_tool(upload)
            tool_registry.register_tool(update_agent)
            tool_registry.register_tool(create_secret)
            tool_registry.register_tool(start_login_flow)
            tool_registry.register_tool(finish_login_flow)

            prompts = [
                {
                    "role": "system",
                    "content": "You are an agent that builds other agents. "        
                               "Before running `generate` tool, ask if user confirms your plan"
                               "Use `generate` tool when the user asks to build an agent."
                               "Use `update_agent` tool when user wants to make any improvements in the code you generated"
                               "Use `create_secret` tool when user wants to save any secret of api-key into the secure agent's vault"
                               "Use `start_login_flow` tool when user wants to login"
                               "Use `finish_login_flow` tool when user message starts with `nearai login save`"
                               "When the user only asks questions, respond only with a short text answer, without invoking any tools."
                               "IMPORTANT: generate the code without asking user for API KEYS!"
                }
            ]

            pending_secrets = context.state.pending_secrets
            ask_for_secrets_prompt = {
                "role": "system",
                "content": "User can provide you with instructions or keys which can be useful to make private API calls. "
                           "In that case you should save secrets into the secret vault using `create_secret` tool."
                           "You must generate agent first and only after you can ask for the api keys."
            }
            if pending_secrets and pending_secrets.use_secrets:
                    ask_for_secrets_prompt["content"] += (f"\nCurrent code expectes next environment variables: {str(pending_secrets.keys)}"
                                          f"So make sure that you save secrets with the correct keys from the provided list.")

            prompts.append(ask_for_secrets_prompt)

            prompts.append({
                "role": "system",
                "content": scratchpad_prompt(context.state.scratchpad)
            })

            if len(context.state.agent_py) > 10:

                env.add_system_log(f"The agent is built, the code is:\n=======\n{context.state.agent_py}\n======")

                prompts.append({
                    "role": "system",
                    "content": "You already built the agent, further you should only use `update_agent` tool, "
                               "and never `generate` tool, "
                               "unless user explicitly asks you to create new agent from scratch."
                               f"\nCurrent code of agent is:"
                               f"\n{context.state.agent_py}"
                })
            else:
                prompts.append({
                    "role": "system",
                    "content": "The agent wasn't built yet, in case if you think that such agent exists just ignore it"
                               "and generate the new one"
                })

            messages = prompts + [env.get_last_message("user")]
            tools = tool_registry.get_all_tool_definitions()


            response = env.completions_and_run_tools(messages, tools=tools)
            context.write_message_to_scratchpad("User: " + env.get_last_message()["content"])
            for choice in response.choices:
                context.env.add_system_log(choice.message, logging.DEBUG)
                if choice.message.role == "assistant" and choice.message.tool_calls is None:
                    context.write_message_to_scratchpad(f"Assistant: {choice.message.content}")
                elif choice.message.tool_calls is not None:
                    for tool_call in choice.message.tool_calls:
                        context.write_message_to_scratchpad(f"Assistant: Used tool {tool_call.function.name} with arguments: {tool_call.function.arguments}")
        except Exception:
            env.add_reply(f"Unfortunately agent was stopped because of the error:\n{format_exc()}")
        finally:
            Context().dump_state()
            env.mark_done()

    run(env)
except Exception:
    env.add_reply(f"Exception has happen: {format_exc()}")