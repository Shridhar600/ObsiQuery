
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