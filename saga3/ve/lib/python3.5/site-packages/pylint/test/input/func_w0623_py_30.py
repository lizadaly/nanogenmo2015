"""Test for W0623, overwriting names in exception handlers."""
# pylint: disable=broad-except,bare-except,pointless-except,print-statement,no-absolute-import
__revision__ = ''

import exceptions

class MyError(Exception):
    """Special exception class."""
    pass


def some_function():
    """A function."""
    exc = None

    try:
        {}["a"]
    except KeyError as xxx_todo_changeme: # W0623
        exceptions.RuntimeError = xxx_todo_changeme # W0623
        pass
    except KeyError as OSError: # W0623
        pass
    except KeyError as MyError: # W0623
        pass
    except KeyError as exc: # this is fine
        print(exc)
    except KeyError as exc1: # this is fine
        print(exc1)
    except KeyError as FOO: # C0103
        print(FOO)

    try:
        pass
    except KeyError as exc1: # this is fine
        print(exc1)

class MyOtherError(Exception):
    """Special exception class."""
    pass


exc3 = None

try:
    pass
except KeyError as xxx_todo_changeme1: # W0623
    exceptions.RuntimeError = xxx_todo_changeme1 # W0623
    pass
except KeyError as xxx_todo_changeme2: # W0623
    exceptions.RuntimeError.args = xxx_todo_changeme2 # W0623
    pass
except KeyError as OSError: # W0623
    pass
except KeyError as MyOtherError: # W0623
    pass
except KeyError as exc3: # this is fine
    print(exc3)
except KeyError as exc4: # this is fine
    print(exc4)
except KeyError as OOPS: # C0103
    print(OOPS)

try:
    pass
except KeyError as exc4: # this is fine
    print(exc4)
except IOError as exc5: # this is fine
    print(exc5)
except MyOtherError as exc5: # this is fine
    print(exc5)
