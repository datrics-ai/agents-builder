import nearai
import json
from typing import Dict
from utils import Context
from nearai.registry import Registry
from nearai.agents.environment import Environment
from traceback import format_exc
from openai.types import FileObject


def _upload(registry: Registry, env: Environment) -> nearai.EntryLocation:
    metadata_path = "metadata.json"

    plain_metadata = json.loads(env.read_file(metadata_path))

    Context().state.metadata = json.dumps(plain_metadata)
    Context().dump_state()

    namespace = nearai.CONFIG.auth.namespace
    name = plain_metadata.pop("name")

    entry_location = nearai.EntryLocation.model_validate(
        dict(
            namespace=namespace,
            name=name,
            version=plain_metadata.pop("version"),
        )
    )

    entry_metadata = nearai.openapi_client.EntryMetadataInput.model_validate(plain_metadata)
    source = entry_metadata.details.get("_source", None)

    if source is not None:
        print(f"Only default source is allowed, found: {source}. Remove details._source from metadata.")
        raise Exception("Only default source is allowed, found: {source}. Remove details._source from metadata.")

    registry.update(entry_location, entry_metadata)

    all_files: Dict[str, FileObject] = {}

    # Traverse all files in the directory `path`
    files_in_thread = env.list_files_from_thread()
    env.add_system_log(f"Traverse all files in the directory `path`: {files_in_thread}")

    for file in files_in_thread:
        # Don't upload state.json file
        if file.filename.find("state.json") >= 0:
            continue
        # Don't upload metadata file.
        if file.filename == metadata_path:
            continue

        saved_file = all_files.get(file.filename, None)
        if saved_file is None:
            all_files[file.filename] = file
        else:
            if saved_file.created_at < file.created_at:
                all_files[file.filename] = file

    env.add_system_log(f"Files to upload: {all_files.values()}")

    if "agent.py" not in all_files:
        # TODO: Dirty hack
        try:
            registry.api.upload_file_v1_registry_upload_file_post(
                path="agent.py",
                file=Context().state.agent_py.encode('utf-8'),
                namespace=entry_location.namespace,
                name=entry_location.name,
                version=entry_location.version,
            )
        except Exception as e:
            Context().env.add_system_log(f"Cannot upload dirty python.py, {format_exc()}")

    for file in all_files.values():
        try:
            registry.api.upload_file_v1_registry_upload_file_post(
                path=file.filename,
                file=env.read_file(file.filename).encode('utf-8'),
                namespace=entry_location.namespace,
                name=entry_location.name,
                version=entry_location.version,
            )
        except nearai.openapi_client.exceptions.BadRequestException as e:
            if isinstance(e.body, str) and "already exists" in e.body:
                raise Exception(f"File already exists at version {entry_location.version}, {e.body}")

            raise e

    return entry_location


def upload(version: str):
    """Release a new version of the agent to users. Call this only when the user asks to do it. For development purposes, use `generate` instead.

    version (str): The version number of the agent.
    """

    env = Context().env

    env.add_system_log("Uploading agent...")
    try:
        env.add_system_log("Updating metadata.json version...")
        metadata = json.loads(env.read_file('metadata.json'))
        metadata['version'] = version
        env.write_file('metadata.json', json.dumps(metadata, indent=2))

        env.add_system_log("Uploading files...")
        registry = Registry()
        registry.api.api_client.configuration.access_token = f"Bearer {nearai.CONFIG.auth.model_dump_json()}"
        agent_id = _upload(registry, env)

        env.add_reply(
            f"Agent uploaded successfully.\n"
            f"Chat with it https://app.near.ai/agents/{agent_id.namespace}/{agent_id.name}/{agent_id.version}\n"
            f"You can give me the feedback and I will make improvements for you!")
        return
    except Exception as e:
        env.add_system_log(f"Error happen when uploading agent, error:\n{format_exc()}")
        return {"error": str(e)}