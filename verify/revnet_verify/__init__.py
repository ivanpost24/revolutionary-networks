"""Support package for the revnet-verify script."""

from pathlib import Path


__version__ = '0.1.0'


PROGRAM_DIR = Path('~/.revnet-verify').expanduser()
PROGRAM_DIR.mkdir(exist_ok=True)
