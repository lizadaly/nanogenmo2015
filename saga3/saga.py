#!/usr/bin/python
# -*- coding: utf-8 -*-

DEFAULT_DELAY = -1000
DEFAULT_NUM_BULLETS = 5

class Thing(object):
    """An object with a name"""
    location = None

    def __init__(self, name=None):
        self.name = name

    def __str__(self):
        if self.location:
            return "the {} is on the {}".format(self.name, self.location.name).capitalize()

class Place(Thing):
    """A Place never has a location, and it doesn't print itself out in the world description"""
    def __str__(self):
        return None

class Person(Thing):
    """A person who has hands and a location and will exhibit behavior"""
    right_hand = None
    left_hand = None
    body = None

    def __str__(self):
        out = []
        if self.right_hand:
            out.append("the {} is in the {}'s right hand".format(self.right_hand.name, self.name))
        if self.left_hand:
            out.append("the {} is in the {}'s left hand".format(self.left_hand.name, self.name))
        if self.body:
            out.append("the {} is on the {}".format(self.body.name, self.name))
        return '; '.join(out).capitalize()

class Gun(Thing):
    
    def __init__(self, name):
        super(Gun, self).__init__(name)
        self.num_bullets = DEFAULT_NUM_BULLETS

def init(delay=DEFAULT_DELAY):
    """Initialize the starting conditions"""
    world = []

    robber = Person('robber')
    robber.location = Thing('window')
    robber.right_hand = Gun('gun')    
    robber.left_hand = Thing('money')
    robber.body = Thing('holster')
    
    sheriff = Person('sheriff')
    sheriff.right_hand = Gun("sheriff's gun")
    sheriff.body = Thing("sheriff's holster")

    table = Thing('table')
    glass = Thing('glass')
    bottle = Thing('bottle')
    glass.location = table
    bottle.location = table
    
    # Append them in the order the original made them appear 
    world.append(robber)
    world.append(glass)
    world.append(bottle)
    world.append(sheriff)
    
    # Start with the world status
    for obj in world:
        print(str(obj) + '.', end=" ")
        
    loop(world)
    
def loop(world):
    """Main story loop, initialized by the delay before the sheriff arrives"""
    print()
    
if __name__ == '__main__':
    # delay = 0 means the SHERIFF arrives immediately
    # delay = input('Select arrival time for SHERIFF:')
    init(delay=DEFAULT_DELAY)
    
