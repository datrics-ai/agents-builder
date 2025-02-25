def scratchpad_prompt(scratchpad: str):
    return f"""
You have memory of the previous conversation with user, it is called scratchpad. 
The scratchpad will be updated automatically.
You should carefully read it before deciding on the next step.
When responding, ensure that you use the scratchpad correctly. 
If multiple steps are needed, iterate through them until you gather all necessary data.

The current scratchpad is:
<scratchpad>
{scratchpad}
</scratchpad>
"""

framework_prompt: str = """
    
Available libraries:
<libraries>
base58 == 2.1.1
pynacl >= 1.5.0
pytz == 2024.2
python_dateutil >= 2.5.3
setuptools >= 21.0.0
urllib3 >= 1.25.3, < 2.1.0
pydantic >=2.8.2
typing-extensions >= 4.7.1
psutil >= 5.9.5
boto3 >= 1.35.3
litellm >= 1.41.0
openai == 1.51.2
chardet
bs4
googlesearch-python >= 1.2.5
PyPDF2
youtube_transcript_api >= 0.6.2
py-near >= 1.1.50
loguru == 0.7.2
ed25519 == 1.5
py-multibase==1.0.3
py-multicodec==0.2.1
pydantic==2.9.2
aiohttp==3.9.3
borsh-construct
tweepy >= 4.14.0
tenacity == 9.0.0
</libraries>

For the agent, you need to use a custom framework, use it when you create or update agent, here's a short documentation on that:
<framework_documentation>
1. You can't directly use `os` module
2. You are given a `env` object that has the following methods:
- env.list_messages() - list of messages in the conversation in format of [{{"role": "user", "content": "message"}}, {{"role": "assistant", "content": "message"}}]. This is an array of Message objects, not a JSON string.
- env.completion(messages) - completion a message to the LLM, returns a string.
- env.add_reply(message) - add a message to the conversation
- env.write_file(filename, content) - write content to a file (use this instead of `open` or `with open`)
- env.read_file(filename) - read the content of a file (use this instead of `open` or `with open`)
- env.get_tool_registry(new=True) - get the tool registry. To use the tool registry, you need to register the tool first using "tool_registry.registry_tool(method)", where method is a Python method name that you defined. It must have a documentation string, and if it has any parameters, they should be documented in the docstring. Tools should not return anything, instead, use `env.add_reply` to add a message to the conversation.
- env.completions_and_run_tools(messages, tools) - run the tools and return the result.
- env.add_system_log(log_message, logging.DEBUG) - write log, always use this method to log responses from APIs
- env.env_vars - it is a dict with environment variables, in case if the api needs authentication use env.env_vars.get("API_KEY") to get the key from environment variables.
3. Don't use any libraries that are not listed in the <libraries> section.
4. Don't use async Python, and don't write classes. Make your code as simple as possible. It's only a prototyping stage.
5. If you use third-party APIs, you can use also APIs that need API Key for authentication. You can ask user for this api key if needed
6. The entire file is run again for every user interaction, so make sure to handle existing message history that you can get by calling `env.list_messages()`.
7. Always add logging for all API requests and responses using env.add_system_log method and do not forget to import logging lib
8. \"env\" is always available in the global context, so do not include it in the parameters of functions
</framework_documentation>

Here are some examples of how to use the framework:
<examples>
    <example>
    
        def generate(agent_name: str):
            \"\"\"Generate a new NEAR AI agent.

            agent_name: The name of the agent. Should match ^[a-zA-Z0-9_\\-.]+$
            \"\"\"

            # Do something

        def upload(version: str):
            \"\"\"Release a new version of the agent to users.

            version: The version number of the agent.
            \"\"\"

            # Do something

        tool_registry = env.get_tool_registry(new=True)
        tool_registry.register_tool(generate)
        tool_registry.register_tool(upload)

        prompt = {{
            "role": "system",
            "content": "You are an agent that builds other agents."
        }}

        env.completions_and_run_tools(
            [prompt] + env.list_messages(),
            tools=tool_registry.get_all_tool_definitions()
        )
    </example>
    <example>
        def run(env: Environment):
            prompt = {{"role": "system", "content": "Act as a slime."}}
            result = env.completion([prompt] + env.list_messages())
            env.add_reply(result)
            env.request_user_input()

        run(env)
    </example>
</examples>
    """

def regenerate_code_prompt(generated_code: str, agent_change_technical_plan: str):
    return f"""You are an agent that builds other AI agents.
You are given a code that you previously generated:
<code>
{generated_code}
</code>

You are given a description of what should be changed in the code:
<description>
{agent_change_technical_plan}
</description>

You need to re-write `agent.py` that implements the agent with the set of changed.

{framework_prompt}

Reply with the code only, nothing else. No formatting, comments, etc., your entire response should be valid Python code. It should be fully working out of the box, so don't add any placeholders or APIs that need API keys.

"""

def generate_code_prompt(agent_technical_plan: str):
    return f"""
You are an agent that builds other AI agents.
You are given a description of the agent you need to build:
<description>
{agent_technical_plan}
</description>

You need to write `agent.py` that implements the agent.

{framework_prompt}

Reply with the code only, nothing else. No formatting, comments, etc., your entire response should be valid Python code. It should be fully working out of the box, so don't add any placeholders or APIs that need API keys.
                """