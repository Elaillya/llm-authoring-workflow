"""Exclusive staging objects with the parent directory's normal permissions."""
import os
from pathlib import Path
import uuid


def temporary_directory(parent, prefix):
    for _ in range(100):
        path=Path(parent)/(prefix+uuid.uuid4().hex)
        try:path.mkdir()
        except FileExistsError:continue
        return path
    raise FileExistsError('Cannot allocate staging directory')


def temporary_file(parent, prefix):
    for _ in range(100):
        path=Path(parent)/(prefix+uuid.uuid4().hex)
        try:fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o666)
        except FileExistsError:continue
        return fd,str(path)
    raise FileExistsError('Cannot allocate staging file')
