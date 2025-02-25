from utils import Context


def ask_user(question: str):
    """
    Sends a message to the user with a question from the agent.
    This function allows to request additional information from a human or confirmation.
    It does not return a response directly but instead writes the question to a shared scratchpad
    or communication channel, where the user can see and respond to it.

    Args:
        question (str): The question that the agent needs to ask the user.
    """

    Context().env.add_system_log(f"Writing to scratchpad:\n{question}")
    Context().write_message_to_scratchpad("Agent: " + question)

    Context().env.set_next_actor("user")
    Context().env.mark_done()