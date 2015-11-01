# pylint: disable=R0903, print-statement, metaclass-assignment
"""test attribute access on metaclass"""


__revision__ = 'yo'

class Meta(type):
    """the meta class"""
    def __init__(cls, name, bases, dictionary):
        super(Meta, cls).__init__(name, bases, dictionary)
        print(cls, cls._meta_args)
        delattr(cls, '_meta_args')

class Test(object, metaclass=Meta):
    """metaclassed class"""
    _meta_args = ('foo', 'bar')

    def __init__(self):
        print('__init__', self)
