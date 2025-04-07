# utils.py
import datetime
import logging

from langchain_core.prompts import PromptTemplate

from prompts import get_prompt


def load_prompt(prompt_name: str, **kwargs: dict) -> str:
    """Loads and formats a prompt.

    Args:
        prompt_name: The name of the prompt to load.
        **kwargs: Keyword arguments to pass to the prompt template.

    Returns:
        The formatted prompt, or an empty string if an error occurred.
    """
    try:
        prompt_template = PromptTemplate(template=get_prompt(prompt_name), input_variables=list(kwargs.keys()))
        prompt = prompt_template.invoke(input=kwargs)
        return str(prompt)
    except Exception as e:
        logging.error(f"Error loading prompt {prompt_name}: {e}")
        return ""


def handle_error(message: str, exception: Exception):
    """Logs an error message and returns a user-friendly error message.

    Args:
        message: A descriptive error message.
        exception: The exception that occurred.

    Returns:
        A user-friendly error message.
    """
    logging.error(f"{message}: {exception}")
    return f"An error occurred: {message}. Please check the logs for details."
