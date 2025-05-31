
from src.models import FileMetadata

def is_valid_metadata(metadata: FileMetadata) -> bool:
    """
    Validates the metadata of a file.

    Args:
        metadata (FileMetadata): The metadata to validate.

    Returns:
        bool: True if the metadata is valid, False otherwise.
    """
    if not metadata.name or not metadata.absolute_path or metadata.size < 0 or metadata.mtime < 0:
        return False
    return True
