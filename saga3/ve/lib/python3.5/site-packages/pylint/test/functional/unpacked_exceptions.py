"""Test for redefine-in-handler, overwriting names in exception handlers."""

def new_style():
    """Some exceptions can be unpacked."""
    try:
        pass
    except IOError as xxx_todo_changeme:  # [unpacking-in-except]
        (errno, message) = xxx_todo_changeme.args  # [unpacking-in-except]
        print(errno, message)  # pylint: disable=print-statement
    # +1: [redefine-in-handler,redefine-in-handler,unpacking-in-except]
    except IOError as xxx_todo_changeme1:
        (new_style, tuple) = xxx_todo_changeme1.args
        print(new_style, tuple)  # pylint: disable=print-statement
