"""Check that instantiating a class with
`abc.ABCMeta` as metaclass fails if it defines
abstract methods.
"""

# pylint: disable=too-few-public-methods, missing-docstring
# pylint: disable=no-absolute-import, metaclass-assignment
# pylint: disable=abstract-method

__revision__ = 0

import abc
from abc import ABCMeta

class GoodClass(object, metaclass=abc.ABCMeta):
    pass

class SecondGoodClass(object, metaclass=abc.ABCMeta):
    def test(self):
        """ do nothing. """

class ThirdGoodClass(object, metaclass=abc.ABCMeta):
    def test(self):
        raise NotImplementedError()

class FourthGoodClass(object, metaclass=ABCMeta):
    pass

class BadClass(object, metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def test(self):
        """ do nothing. """

class SecondBadClass(object, metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def test(self):
        """ do nothing. """

class ThirdBadClass(object, metaclass=ABCMeta):
    @abc.abstractmethod
    def test(self):
        pass

class FourthBadClass(ThirdBadClass):
    pass


def main():
    """ do nothing """
    GoodClass()
    SecondGoodClass()
    ThirdGoodClass()
    FourthGoodClass()
    BadClass() # [abstract-class-instantiated]
    SecondBadClass() # [abstract-class-instantiated]
    ThirdBadClass() # [abstract-class-instantiated]
    FourthBadClass() # [abstract-class-instantiated]
