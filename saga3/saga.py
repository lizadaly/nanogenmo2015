#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import coloredlogs
coloredlogs.install(level=logging.DEBUG)

log = logging.getLogger()

DEFAULT_SHERIFF_DELAY = 5
DEFAULT_NUM_BULLETS = 5
DEFAULT_HEALTH = 5
MAX_TURNS = 20

# Initiatives
HIGH_INITIATIVE = 20
MEDIUM_INITIATIVE = 10
DEFAULT_INITIATIVE = 1

def check_initiative(actors):
    """For each actor, find out who gets to move next"""
    return max(actors, key=lambda x: x.initiative(), default=actors[0])

def action(stage, actor):
    """At each step, evaluate what happens next"""
    # By default, let the current actor do his thing
    if stage.elapsed_time > MAX_TURNS:
        return actor

    actor.set_starting_location(actor.default_location)
    actor.act()

    stage.elapsed_time += 1

    # Determine who acts next
    next_actor = check_initiative(stage.actors)

    # If it's the same actor, just call this again
    if next_actor == actor:
        return action(stage, actor)

    return next_actor

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
    stage = None  # Hook for the world model
    enemy = None  # Kinda cheating but makes things easy
    default_location = None
    health = 0  # 0 is bad, but we'll revive them on init

    def initiative(self):
        """Return a value representative of how much this actor wants to do something based on their state"""
        actor_initiative = 0
        if len(self.path) > 0:  # Actor really wants to be somewhere
            actor_initiative += HIGH_INITIATIVE

        return actor_initiative

    def act(self):
        """Do whatever is the next queued event"""
        # If there's a target location, try to go there
        if len(self.path) > 0:
            next_location = self.path[0]
            log.debug("Trying to go to next location %s", next_location)
            print("go {} {}".format('through' if next_location.is_openable and next_location.is_open else 'to',
                                    next_location))
            if self.go(next_location):
                # If going there was successful, set their new location and drop it from the path
                self.path = self.path[1:]

    def go(self, location):
        """Try to move to the next location. If that location can be opened, like a door, open it first
        and return False (we didn't actually 'go'). Otherwise, set the new location."""
        if not location.is_open:
            print("open {}".format(location.name))
            location.is_open = True
            return False
        self.location = location
        return True

    def has(self, obj_name):
        """Does the actor have the named object in any of its body parts? If so, return the container where it is"""
        if obj_name == self.right_hand.name:
            return self.right_hand
        if obj_name == self.left_hand.name:
            return self.left_hand
        if obj_name == self.body.name:
            return self.body

    @property
    def is_alive(self):
        return self.health > 0

    def set_starting_location(self, location):
        """Setting the starting location changes the world model and also prints an explicit
        message. It's idempotent and so safe to call in a loop because I'm lazy"""
        if location and not self.location:
            self.location = location
            print("(The {} is at the {}.)".format(self.name, self.location.name))

    def drop(self, obj, target):
        """Drop an object in a place or on a supporting object. Is a no-op if the actor doesn't have the object."""
        if self.has(obj):

            # Is the location a place or a supporter? A supporter will itself have a location; a place won't.
            if hasattr(target.location, 'location'):
                print("put {} down at {}".format(obj.name, target.location.name))
            else:
                print("put {} on {}".format(obj.name, target.name))
            obj.location = target


    def __init__(self, name):
        super(Person, self).__init__(name)
        self.path = []
        self.health = DEFAULT_HEALTH

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
    """The Robber wants to deposit the money, drink, kill the sheriff, and escape with the money"""
    def initiative(self):
        actor_initiative = super(Robber, self).initiative()

        # If the Robber has the money and the Sheriff is alive,
        # the Robber wants to drop the money in the Corner
        if self.has('money') and self.enemy.is_alive:
            actor_initiative += HIGH_INITIATIVE

        log.debug("%s is returning initiative %s", self.name, actor_initiative)
        return actor_initiative

    def act(self):
        """A set of conditions of high priority; these actions will be executed first"""
        if self.location.name == 'corner' and self.has('money') and self.enemy.is_alive:
            money = self.has('money')
            self.drop(money, self.location)
            return True
        return super(Robber, self).act()

class Sheriff(Person):
    """The Sheriff wants to kill the Robber and leave with the money. He does not drink and arrives
    on a delay."""
    def __init__(self, name, delay):
        super(Sheriff, self).__init__(name)
        self.delay = delay

    def initiative(self):
        actor_initiative = super(Sheriff, self).initiative()

        # The Sheriff is subject to the global timer and will do nothing until it expires
        if self.stage.elapsed_time < self.delay:
            return 0

        log.debug("%s is returning initiative %s", self.name, actor_initiative)
        return actor_initiative

class Gun(Thing):
    """A Gun is an object with a distinct property of being shootable and having a number of bullets"""
    def __init__(self, name):
        super(Gun, self).__init__(name)
        self.num_bullets = DEFAULT_NUM_BULLETS

class Stage(object):
    """The world model"""
    elapsed_time = 0

    @property
    def actors(self):
        """Returns all the objects in the world that are people"""
        return [obj for obj in self.objects if hasattr(obj, 'body')]

    def __init__(self):
        self.objects = []

def init(delay):
    """Initialize the starting conditions"""
    stage = Stage()

    # Humans
    robber = Robber('robber')
    robber.right_hand = Gun('gun')
    robber.left_hand = Thing('money')
    robber.body = Thing('holster')
    robber.stage = stage  # A mechanism to get ahold of the world state

    sheriff = Sheriff('sheriff', delay=delay)
    sheriff.right_hand = Gun("sheriff's gun")
    sheriff.body = Thing("sheriff's holster")
    sheriff.stage = stage
    robber.enemy = sheriff
    sheriff.enemy = robber

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
    stage.objects.append(robber)
    stage.objects.append(glass)
    stage.objects.append(bottle)
    stage.objects.append(sheriff)

    # Start with the world status
    for obj in stage.objects:
        print(str(obj) + '.', end=" ")

    loop(stage)

def loop(stage):
    """Main story loop, initialized by the delay before the sheriff arrives"""
    print()
    next_actor = stage.actors[0]
    while stage.elapsed_time < MAX_TURNS:
        print()
        print(next_actor.name.upper())
        next_actor = action(stage, next_actor)


if __name__ == '__main__':
    # delay = 0 means the SHERIFF arrives immediately
    # delay = input('Select arrival time for SHERIFF:')
    init(delay=DEFAULT_SHERIFF_DELAY)
