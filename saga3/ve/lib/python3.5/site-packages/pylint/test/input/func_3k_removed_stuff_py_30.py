"""test relative import"""
# pylint: disable=no-absolute-import
__revision__ = [_f for _f in map(str, (1, 2, 3)) if _f]


from . import func_w0302

def function():
    """something"""
    print(func_w0302)
    unic = "unicode"
    low = unic.looower
    return low
