from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from numpy import long

@dataclass
class FileMetadata:
    name: str
    absolute_path: str
    size: int
    mtime: float  # Last modified time as a Unix timestamp
    
