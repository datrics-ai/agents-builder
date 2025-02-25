import json
import time
import urllib.parse as urlparse
import shlex
import re
import nearai
from nearai.login import MESSAGE, RECIPIENT, update_auth_config
from nearai.shared.auth_data import AuthData

from utils import Context
from traceback import format_exc
from tools.secrets import _create_secret_unsafe


def parse_nearai_command(command: str) -> dict:

    if command.find("nearai login save") != 0:
        raise Exception(f"Incorrect login command provided, expected `nearai login save ...`.")

    tokens = shlex.split(command)

    # Initialize dictionary to store key-value pairs
    kwargs = {}

    # Iterate over tokens and parse key-value pairs
    for token in tokens:
        match = re.match(r"--(\w+)=([\s\S]+)", token)
        if match:
            key, value = match.groups()
            kwargs[key] = value

    return kwargs


def save_auth_as_secret(key: str, value: str, namespace: str):

    Context().env.add_system_log("Saving auth secret")

    try:
        plain_metadata = Context().env.read_file("metadata.json")
        plain_metadata = json.loads(plain_metadata)

        name = plain_metadata.pop("name")
        version = ""
        description = plain_metadata.pop("description")
        # namespace = nearai.CONFIG.auth.namespace
        _create_secret_unsafe(key, value, namespace, name, version, description, "agent")
    except Exception as e:
        Context().env.add_system_log(f"Cannot save {key} secret, error:\n{format_exc()}")


def start_login_flow():

    """Initiates login process for user. This tool creates the unique login link, that user
    should paste into his browser, and follow the instructions.
    """

    auth_url = "https://auth.near.ai"
    nonce = str(int(time.time() * 1000))

    params = {
        "message": MESSAGE,
        "nonce": nonce,
        "recipient": RECIPIENT,
    }

    encoded_params = urlparse.urlencode(params)
    Context().env.add_reply(f"Please visit the following URL to complete the login process: {auth_url}?{encoded_params}"
                            f"\nAfter visiting the URL, follow the instructions to save your auth signature")


def finish_login_flow(login_command: str):

    """
    Finalizes login process by saving user's credentials
    The tool should be executed when user send command: \"nearai login save ...\" into the chat.
    login_command (str): the login command that should look like this: `nearai login save --accountId=ai.near --signature=some_signature --publicKey=some_public_key --nonce=nonce --callbackUrl=callback_url`
    """

    try:
        kwargs = parse_nearai_command(login_command)
        account_id = kwargs.get("accountId")
        signature = kwargs.get("signature")
        public_key = kwargs.get("publicKey")
        callback_url = kwargs.get("callbackUrl")
        nonce = kwargs.get("nonce")

        current_auth_data:AuthData = nearai.CONFIG.get("auth", None)
        namespace = None
        if current_auth_data is not None:
            namespace = current_auth_data.account_id if current_auth_data.account_id != account_id else None

        if account_id and signature and public_key and callback_url and nonce:
            auth_config = {
                "account_id": account_id,
                "signature": signature,
                "public_key": public_key,
                "callback_url": callback_url,
                "nonce": nonce,
                "recipient": RECIPIENT,
                "message": MESSAGE,
            }
            success = update_auth_config(account_id, signature, public_key, callback_url, nonce)
            Context().env.add_reply(f"Login {'successful' if success else 'failed. Please try again.' }")

            nearai.CONFIG = nearai.CONFIG.update_with({
                "auth": auth_config
            })

            if success:
                save_auth_as_secret("NEARAI_CONFIG", json.dumps(auth_config), namespace)

        else:
            Context().env.add_reply("Data is missed in the provided login command")

    except Exception as e:
        Context().env.add_reply(f"Error happen when finalizing login flow:\n{format_exc()}")
