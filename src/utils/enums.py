from enum import Enum

class Status(Enum):
    """
    Enum for file status in the database.
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"