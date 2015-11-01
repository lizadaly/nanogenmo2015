#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import coloredlogs
coloredlogs.install(level=logging.INFO)

log = logging.getLogger()

DEFAULT_DELAY = 10
DEFAULT_NUM_BULLETS = 5
WORLD_LOOP = 10

def action(stage, actor):
    """At each step, evaluate what happens next"""
    # By default, let the current actor do his thing
    actor.act()

    
class Thing(object):
    """An object with a name"""
    location = None

    def __init__(self, name=None):
        self.name = name

    def __str__(self):
        if self.location:
            return "the {} is on the {}".format(self.name, self.location.name).capitalize()
        return self.name
    
class Place(Thing):
    """A Place never has a location, and it doesn't print itself out in the world description."""
    is_open = True    
    is_openable = False

class Door(Place):
    """A door is a place that can be open or closed. If it's open, we'll print a different message when the actor
    moves through it than an ordinary place"""
    is_openable = True
    is_open = False
    
class Person(Thing):
    """A person who has hands and a location and will exhibit behavior"""
    right_hand = None
    left_hand = None
    body = None

    def act(self):
        # If there's a target location, try to go there
        if len(self.path) > 0:
            next_location = self.path[0]
            log.debug("Trying to go to next location %s", next_location)
            print("go {} {}".format('through' if next_location.is_openable and next_location.is_open else 'to',
                                    next_location), end=" ") 
            if self.go(next_location):
                # If going there was successful, 
                self.location = next_location
                self.path = self.path[1:]
    
    def go(self, location):
        if not location.is_open:
            print("open {}".format(location.name), end=" ")
            location.is_open = True
            return False
        return True

    def set_starting_location(self, location):
        """Setting the starting location changes the world model and also prints an explicit message. It's idempotent 
        and so safe to call in a loop because I'm lazy"""
        if location and not self.location:
            self.location = location
            print("(The {} is at the {}.)".format(self.name, self.location.name), end=" ")
        
    def __init__(self, name):
        super(Person, self).__init__(name)
        self.path = []
        
    def __str__(self):
        out = []
        if self.right_hand:
            out.append("the {} is in the {}'s right hand".format(self.right_hand.name, self.name))
        if self.left_hand:
            out.append("the {} is in the {}'s left hand".format(self.left_hand.name, self.name))
        if self.body:
            out.append("the {} is on the {}".format(self.body.name, self.name))
        return '; '.join(out).capitalize()

class Robber(Person):
    pass
class Sheriff(Person):
    pass

class Gun(Thing):
    
    def __init__(self, name):
        super(Gun, self).__init__(name)
        self.num_bullets = DEFAULT_NUM_BULLETS

def init(delay=DEFAULT_DELAY):
    """Initialize the starting conditions"""
    stage = []

    # Humans
    robber = Robber('robber')
    robber.right_hand = Gun('gun')    
    robber.left_hand = Thing('money')
    robber.body = Thing('holster')
    
    sheriff = Sheriff('sheriff')
    sheriff.right_hand = Gun("sheriff's gun")
    sheriff.body = Thing("sheriff's holster")

    # Places
    window = Place('window')
    table = Place('table')
    door = Door('door')
    corner = Place('corner')
    
    sheriff.default_location = None  # nowhere
    robber.default_location = window
    robber.path = [door, corner]
    
    # Objects
    glass = Thing('glass')
    bottle = Thing('bottle')
    glass.location = table
    bottle.location = table

    # Append them in the order the original made them appear
    stage.append(robber)
    stage.append(glass)
    stage.append(bottle)
    stage.append(sheriff)

    # Start with the world status
    for obj in stage:
        print(str(obj) + '.', end=" ")

    loop(stage)
    
def loop(stage):
    """Main story loop, initialized by the delay before the sheriff arrives"""
    print()
    counter = WORLD_LOOP
    while counter > 0:
        actors = [obj for obj in stage if hasattr(obj, 'body')]
        for actor in actors:
            print(); print(); print(actor.name.upper())
            actor.set_starting_location(actor.default_location)
            action(stage, actor)
            counter -= 1
            
if __name__ == '__main__':
    # delay = 0 means the SHERIFF arrives immediately
    # delay = input('Select arrival time for SHERIFF:')
    init(delay=DEFAULT_DELAY)
    
