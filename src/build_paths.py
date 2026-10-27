"""Common output paths; release builds never overwrite the active local driver/apps."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BUILD=Path(os.environ.get('HD300_BUILD_DIR',ROOT/'build')).resolve()
LOGS=Path(os.environ.get('HD300_LOG_DIR',ROOT/'logs')).resolve()
VERSION=(ROOT/'VERSION').read_text().strip()
BUILD.mkdir(parents=True,exist_ok=True)
LOGS.mkdir(parents=True,exist_ok=True)
