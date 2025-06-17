from langchain_core.messages import BaseMessage
from typing import List, Optional
from src.models import FileMetadata
from datetime import datetime, timezone


def is_valid_metadata(metadata: FileMetadata) -> bool:
    """
    Validates the metadata of a file.

    Args:
        metadata (FileMetadata): The metadata to validate.

    Returns:
        bool: True if the metadata is valid, False otherwise.
    """
    if not metadata.file_name or not metadata.file_path or metadata.file_size < 0 or metadata.last_modified < 0:
        return False
    return True

def get_system_time_info()-> dict:
    utc_now =  datetime.now(timezone.utc)
    local_tz = datetime.now().astimezone().tzinfo
    day_of_week = datetime.now().strftime("%A")

    return {
        "current_utc_datetime": utc_now,
        "local_timezone": str(local_tz),
        "day_of_week": day_of_week,
    }

def format_recent_history(messages: List[BaseMessage], last_n: int = 5) -> str:
    """Formats the last N messages into a string for the prompt."""
    if not messages:
        return "No recent conversation history."
    
    recent_messages = messages[ -last_n :]
    formatted_lines = []
    for msg in recent_messages:
        role = "User" if msg.type == "human" else "Assistant" if msg.type == "ai" else "tool Response" if msg.type == "tool" else msg.type
        formatted_lines.append(f"{role}: {msg.content}")
    return "\n".join(formatted_lines)

def get_formatted_convo_history(state):
    message_history: Optional[List[BaseMessage]] = state["messages"]
    formatted_history: str = "No recent conversation history provided."
    if message_history:
        formatted_history = format_recent_history(message_history, last_n=5)
    return formatted_history