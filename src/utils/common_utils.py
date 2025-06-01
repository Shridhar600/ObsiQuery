
from src.models import FileMetadata

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
