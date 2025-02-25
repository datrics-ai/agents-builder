import json
import logging
import nearai
from nearai.openapi_client.models import CreateHubSecretRequest, RemoveHubSecretRequest
from nearai.openapi_client.api import HubSecretsApi
from utils import Context
from traceback import format_exc


def _get_secrets():
    try:
        hub_secrets = HubSecretsApi()
        hub_secrets.api_client.configuration.access_token = f"Bearer {nearai.CONFIG.auth.model_dump_json()}"
        result = hub_secrets.get_user_secrets_v1_get_user_secrets_get()
        return result
    except Exception as e:
        Context().env.add_system_log(f"Secrets were not fetched because of error:\n {format_exc()}")
        return []


def _delete_secret_unsafe(key: str, namespace: str, name: str, version: str, category: str = "agent"):
    try:
        hub_secrets = HubSecretsApi()
        hub_secrets.api_client.configuration.access_token = f"Bearer {nearai.CONFIG.auth.model_dump_json()}"
        request = RemoveHubSecretRequest.model_validate(
            dict(
                namespace=namespace,
                name=name,
                version=version,
                key=key,
                category=category
            )
        )
        result = hub_secrets.remove_hub_secret_v1_remove_hub_secret_post(request)
        Context().env.add_system_log(f"Secret {key} was deleted: {result}")
    except Exception as e:
        Context().env.add_system_log(f"Secret {key} was not deleted.", logging.DEBUG)
        return False

    return True


def _create_secret_unsafe(key: str, value: str, namespace: str, name: str, version: str, description: str, category: str = "agent"):
    _delete_secret_unsafe(key, namespace, name, version, category)

    try:
        hub_secret_request = CreateHubSecretRequest.model_validate(
            dict(
                namespace=namespace,
                name=name,
                version=version,
                description=description,
                key=key,
                value=value,
                category=category
            )
        )

        hub_secrets = HubSecretsApi()
        Context().env.add_system_log(f"Saving secret with Bearer: {nearai.CONFIG.auth.model_dump_json()}")
        hub_secrets.api_client.configuration.access_token = f"Bearer {nearai.CONFIG.auth.model_dump_json()}"
        result = hub_secrets.create_hub_secret_v1_create_hub_secret_post(hub_secret_request)
        Context().env.add_system_log(f"Secret was saved successfully: {str(result)}")
    except Exception:
        Context().env.add_system_log(f"Secret was not saved because of error:\n {format_exc()}")
        return False

    return True


def create_secret(key: str, value: str):
    """
    Saves key-value pair (secret) in the agent's secure storage
    key (str): The name of the secret
    value (str): The value of the secret
    """

    namespace = nearai.CONFIG.auth.namespace
    plain_metadata = Context().state.metadata
    if plain_metadata is None or len(plain_metadata) == 0:
        Context().env.add_reply("I cannot create secret for you because I should create an agent first.")
        return

    try:
        plain_metadata = json.loads(plain_metadata)
    except Exception:
        Context().env.add_reply("I cannot create secret for you because I should create an agent first.")
        return

    name = plain_metadata.pop("name")
    version = ""
    description = plain_metadata.pop("description")
    _create_secret_unsafe(key, value, namespace, name, version, description, "agent")

    Context().env.add_reply(f"I've saved {key} for you.")