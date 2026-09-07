"""Test-only launcher that emulates cp949 defaults for text-file I/O.

Explicit encodings, binary I/O and standard streams retain their normal behavior.
This is not a replacement for native Windows testing or a runtime workaround.
"""
from contextlib import contextmanager
import io
from pathlib import Path
import runpy
import sys
from unittest.mock import patch


@contextmanager
def cp949_file_defaults():
    original_open = io.open

    def locale_open(file, mode="r", buffering=-1, encoding=None, errors=None,
                    newline=None, closefd=True, opener=None):
        if "b" not in mode and encoding in (None, "locale"):
            encoding = "cp949"
        return original_open(file, mode, buffering, encoding, errors, newline, closefd, opener)

    def text_encoding(encoding, stacklevel=2):
        return "cp949" if encoding in (None, "locale") else encoding

    # pathlib resolves an omitted encoding before io.open on Python 3.10+.
    with patch("io.text_encoding", text_encoding), patch("io.open", locale_open), \
            patch("builtins.open", locale_open):
        yield


if __name__ == "__main__":
    sys.argv = sys.argv[1:]
    sys.path.insert(0, str(Path(sys.argv[0]).resolve().parent))
    with cp949_file_defaults():
        runpy.run_path(sys.argv[0], run_name="__main__")
