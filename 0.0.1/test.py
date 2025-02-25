import json

from tools.secrets import _delete_secret_unsafe, _get_secrets

# _delete_secret_unsafe("NEARAI_CONFIG", "kirikiri.near", "datrics-agent-builder", "", "user")
# _delete_secret_unsafe("NEARAI_CONFIG", "kirikiri.near", "datrics-agent-builder", "", "agent")
# _delete_secret_unsafe("NEARAI_CONFIG", "kirikiri.near", "datrics-agent-builder", "0.0.14", "user")

# from tools.login import parse_nearai_command
# from nearai.login import RECIPIENT, MESSAGE
# import nearai
#
# kwargs = parse_nearai_command(login_command)
# account_id = kwargs.get("accountId")
# signature = kwargs.get("signature")
# public_key = kwargs.get("publicKey")
# callback_url = kwargs.get("callbackUrl")
# nonce = kwargs.get("nonce")
#
# auth_config = {
#                 "account_id": account_id,
#                 "signature": signature,
#                 "public_key": public_key,
#                 "callback_url": callback_url,
#                 "nonce": nonce,
#                 "recipient": RECIPIENT,
#                 "message": MESSAGE,
#                 "on_behalf_of": None
#             }
#
# nearai.CONFIG = nearai.CONFIG.update_with({"auth": auth_config})

secrets = _get_secrets()
print(secrets)


# _delete_secret_unsafe("NEARAI_CONFIG", "kirikiritest1.near", "datrics-agent-builder", "", "agent")
