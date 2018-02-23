from contextlib import contextmanager
import os

@contextmanager
def req_file(filename, contents):
    with open(filename, 'w') as file:
        file.write(contents)
    try:
        yield
    finally:
        os.unlink(filename)
