""" This should not warn about `prop` being abstract in Child """
# pylint: disable=too-few-public-methods, no-absolute-import,metaclass-assignment

import abc

class Parent(object, metaclass=abc.ABCMeta):
    """Abstract Base Class """

    @property
    @abc.abstractmethod
    def prop(self):
        """ Abstract """

class Child(Parent):
    """ No warning for the following. """
    prop = property(lambda self: 1)
