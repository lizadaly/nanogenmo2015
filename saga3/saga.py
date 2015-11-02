#!/usr/bin/python
# -*- coding: utf-8 -*-

import inspect
import logging
import random
import sys

import coloredlogs
coloredlogs.install(level=logging.DEBUG)
coloredlogs.install(level=logging.INFO)
log = logging.getLogger()

DEFAULT_SHERIFF_DELAY = 15
DEFAULT_NUM_BULLETS = 5
DEFAULT_HEALTH = 5
MAX_TURNS = 100

# Initiatives
HIGH_INITIATIVE = 30
MEDIUM_INITIATIVE = 20
DEFAULT_INITIATIVE = 10

GUN_DAMAGE = {'miss': {'health': 0,
                       'message': 'MISSED'},
              'nick': {'health': -1,
                       'message': '{} NICKED'},
              'hit': {'health': -2,
                      'message': '{} HIT'}}

class Stage(object):
    """The world model"""
    elapsed_time = 0

    @property
    def actors(self):
        """Returns all the objects in the world that are people"""
        return [obj for obj in self.objects if hasattr(obj, 'body')]

    def find(self, obj_name):
        """Find an object by name in the world and return the object"""
        return next(obj for obj in self.objects + self.places if obj.name == obj_name)

    def __init__(self):
        self.objects = []
        self.places = []

stage = Stage()

def check_initiative(actors):
    """For each actor, find out who gets to move next"""
    return max(actors, key=lambda x: x.initiative(), default=actors[0])

def action(actor):
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
        return action(actor)

    return next_actor

class Thing(object):
    """An object with a name"""
    location = None

    def move_to(self, place):
        """Move an object from a current container (if it has one) to a new one."""
        # Drop it from its current location if it has one
        if self.location:
            self.location = None
        self.location = place

    def __init__(self, name, preposition='on'):
        stage.objects.append(self)
        self.name = name
        self.preposition = preposition

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def status(self):
        if self.location and not isinstance(self.location, Person):  # Don't print the status of body parts
            if isinstance(self.location, Place):
                return "the {} is {} the {}".format(self.name, self.location.preposition, self.location.name).capitalize()
            if isinstance(self.location, Thing):
                return "the {} is {} the {}".format(self.name, self.location.preposition, self.location.name).capitalize()

class Place(Thing):
    """A Place never has a location, and it doesn't print itself out in the world description."""
    is_open = True
    is_openable = False

    def __init__(self, name=None):
        super(Place, self).__init__(name)
        stage.places.append(self)

class Door(Place):
    """A door is a place that can be open or closed. If it's open, we'll print a different message when the actor
    moves through it than an ordinary place"""
    is_openable = True
    is_open = False

    def close(self):
        print("close door")
        self.is_open = False

    def open(self):
        print("open door")
        self.is_open = True

class Person(Thing):
    """A person who has hands and a location and will exhibit behavior"""
    stage = None  # Hook for the world model
    enemy = None  # Kinda cheating but makes things easy
    default_location = None
    health = 0  # -1 is dead, but we'll revive them on init
    is_dead = False

    def initiative(self):
        """Return a value representative of how much this actor wants to do something based on their state"""
        if self.is_dead:  # If they're already dead they're pretty lacking in initiative
            return -9999

        # If they _just_ died, give them a huge initiative bonus so we "cut" to their scene
        if self.health <= 0:
            return 9999

        actor_initiative = random.randrange(0, DEFAULT_INITIATIVE)

        if len(self.path) > 0:  # Actor really wants to be somewhere
            actor_initiative += HIGH_INITIATIVE
            log.debug("+ %s init change for path movement: %s/%s", self.name, HIGH_INITIATIVE, actor_initiative)

        # If they're injured they're pretty mad
        injury_bonus = DEFAULT_HEALTH - self.health
        actor_initiative += injury_bonus
        log.debug("+ %s init change for injury bonus: %s/%s", self.name, injury_bonus, actor_initiative)

        # They're also more excited if they're almost out of bullets
        if self.get_if_held(Gun):
            bullet_bonus = 10 if self.get_if_held(Gun).num_bullets == 1 else 0
            actor_initiative += bullet_bonus
            log.debug("- %s init change for bullet bonus: %s/%s", self.name, bullet_bonus, actor_initiative)

        return max(1, actor_initiative)

    def act(self):
        """Do whatever is the next queued event"""
        # If the actor just died, oops
        if self.health <= 0:
            print("{} dies.".format(self.name))
            self.is_dead = True
            return

        # If there's a queued event, hit that first
        if len(self.queue) > 0:
            cmd, args = self.queue[0]
            if args:
                cmd(args)
            else:
                cmd()
            self.queue = self.queue[1:]
            return

        # If there's a target location, try to go there
        if len(self.path) > 0:
            next_location = self.path[0]
            if self.go(next_location):
                # If going there was successful, set their new location and drop it from the path
                self.path = self.path[1:]
            return

        # If the enemy is present, try to kill them!
        if self.enemy_is_present():
            # Pretend for now that you have the gun
            self.shoot(self.enemy)
            return

        # If the enemy is dead, take the money and run
        if self.enemy.is_dead:
            log.debug("*** Trying to get the money")
            money = self.stage.find('money')
            if self.location == money.location:
                return self.take(money)
            # End game! Flee with the money!
            if self.get_if_held('money'):
                self.path = ['door', None]
                self.escaped = True

        # Try to get a random drink
        container = stage.find(random.choice(('glass', 'bottle')))
        # If we're holding it, just drink it
        if self.get_if_held(container):
            print("take a drink from {}".format(container))
            return True

        if self.can_reach_obj(container):
            self.take(container)
            return True

        self.go_to_random_location()

    def can_reach_obj(self, obj):
        """True if the Person can reach the object in question. The object must be either directly
        in the same location, or on a visible supporter in the location"""
        if self.location == obj.location:
            return True
        if hasattr(obj.location, 'location') and obj.location.location == self.location:
            return True

    def take(self, obj):
        """Try to take an object. If there's no hand available, drop an object and queue taking
        the object. Return True if the object was taken or False if no hands available."""
        right_obj = self.get_held_obj(self.right_hand)
        if not right_obj:
            print("Pick up the {} with the {}".format(obj.name, self.right_hand.name))
            obj.move_to(self.right_hand)
            return True
        left_obj = self.get_held_obj(self.left_hand)
        if not left_obj:
            print("Pick up the {} with the {}".format(obj.name, self.left_hand.name))
            obj.move_to(self.left_hand)
            return True

        # Drop the thing in the right hand by default
        self.drop(right_obj, self.location)
        self.queue.append((self.take, obj))


    def go_to_random_location(self):
        """Randomly go to a location that isn't the current one"""
        location = random.choice([place for place in stage.places if place != self.location])
        self.go(location)

    def enemy_is_present(self):
        """Is the enemy visible and suitably shootable?"""
        log.debug(self.enemy.name)
        log.debug(self.enemy.location)
        log.debug(self.enemy.is_alive)
        return self.enemy.location != None and self.enemy.is_alive

    def shoot(self, target):
        """Shoot first, ask questions never"""
        gun = self.get_if_held(Gun)
        if gun:
            print("fire!")
            log.debug("%s is trying to shoot %s", self.name, target.name)
            hit_weight = 1
            if gun.num_bullets == 1:
                hit_weight += 1
            if self.health < DEFAULT_HEALTH:
                hit_weight += 1

            weighted_hit_or_miss = [('miss', 3), ('nick', 5 * hit_weight), ('hit', 1 * hit_weight)]
            hit_or_nick = random.choice([val for val, cnt in weighted_hit_or_miss for i in range(cnt)])
            print(GUN_DAMAGE[hit_or_nick]['message'].format(target.name))
            target.health += GUN_DAMAGE[hit_or_nick]['health']
            gun.num_bullets -= 1


    def go(self, location):
        """Try to move to the next location. If that location can be opened, like a door, open it first.
        Otherwise, set the new location.  If `location` is a string, find the
        name of that location in the world."""

        if isinstance(location, str):
            location = self.stage.find(location)

        log.debug("Trying to go to next location %s", location)
        if not location and self.escaped:
            print("CURTAIN")
            sys.exit(0)

        if location.is_openable and not location.is_open:
            location.open()
            return False

        if location.is_openable and location.is_open:
            print("go through {}".format(location))
            self.queue.append((location.close, None))
        else:
            print("go to {}".format(location))

        self.location = location
        return True

    def get_if_held(self, obj_name):
        """Does the actor have the object name, object, or classname in any of its body parts? If so, return the container where it is"""
        # First check if it's a classname (like Gun)
        if inspect.isclass(obj_name):
            # Check all the world models for objects of this type and try to find a match
            for obj in stage.objects:
                if isinstance(obj, obj_name) and obj.location in self.parts:
                    return obj

        if isinstance(obj_name, str):
            # If not try to find the named object
            obj = self.stage.find(obj_name)
        else:
            obj = obj_name
        if obj.location in self.parts:
            return obj

    def get_held_obj(self, part):
        """Get the object held by a given body part. Returns None if the body part isn't holding anything"""
        for obj in stage.objects:
            if obj.location == part:
                return part

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
        if self.get_if_held(obj.name):

            # Is the location a place or a supporter? A supporter will itself have a location; a place won't.
            if hasattr(target.location, 'location'):
                print("put {} down at {}".format(obj.name, target.location.name))
            else:
                print("put {} on {}".format(obj.name, target.name))
            obj.move_to(target)

    def __init__(self, name):
        super(Person, self).__init__(name)
        self.health = DEFAULT_HEALTH
        self.path = []  # A path of Places the person is currently walking
        self.queue = []  # A queue of functions to call next
        self.right_hand = Thing("{}'s right hand".format(self.name), preposition='in')
        self.left_hand = Thing("{}'s left hand".format(self.name), preposition='in')
        self.body = Thing("{}".format(self.name))
        self.parts = [self.left_hand, self.right_hand, self.body]
        self.escaped = False  # The final endgame state

class Robber(Person):
    """The Robber wants to deposit the money, drink, kill the sheriff, and escape with the money"""
    def initiative(self):
        actor_initiative = super(Robber, self).initiative()

        # If the Robber has the money and the Sheriff is alive,
        # the Robber wants to drop the money in the Corner
        if self.get_if_held('money') and self.enemy.is_alive:
            actor_initiative += HIGH_INITIATIVE

        log.debug("%s is returning initiative %s", self.name, actor_initiative)
        return actor_initiative

    def act(self):
        """A set of conditions of high priority; these actions will be executed first"""

        if self.location.name == 'corner' and self.get_if_held('money') and self.enemy.is_alive:
            money = self.get_if_held('money')
            self.drop(money, self.location)
            return True
        return super(Robber, self).act()


class Sheriff(Person):
    """The Sheriff wants to kill the Robber and leave with the money. He does not drink as often and arrives
    on a delay."""
    def __init__(self, name, delay):
        super(Sheriff, self).__init__(name)
        self.delay = delay

    def initiative(self):
        actor_initiative = super(Sheriff, self).initiative()

        # The Sheriff is subject to the global timer and will do nothing until it expires
        if self.stage.elapsed_time < self.delay:
            actor_initiative = 0

        elif self.location == None:
            # If they haven't moved, tell them they want to move to the table
            actor_initiative += HIGH_INITIATIVE

        log.debug("%s is returning initiative %s", self.name, actor_initiative)
        return actor_initiative

    def act(self):
        """The Sheriff wants to get in the house right away"""
        if self.location == None:
            self.path = ['window', 'door']
        return super(Sheriff, self).act()

class Gun(Thing):
    """A Gun is an object with a distinct property of being shootable and having a number of bullets"""
    def __init__(self, name):
        super(Gun, self).__init__(name)
        self.num_bullets = DEFAULT_NUM_BULLETS

class Container(Thing):
    """A Container is a vessel that can contain a thing (whisky)"""
    def __init__(self, name):
        super(Container, self).__init__(name)
        self.full = False

def init(delay):
    """Initialize the starting conditions"""

    # Humans
    robber = Robber('robber')
    robber_gun = Gun('gun')
    robber_gun.move_to(robber.right_hand)
    money = Thing('money')
    money.move_to(robber.left_hand)
    robber_holster = Thing('holster')
    robber_holster.move_to(robber.body)
    robber.stage = stage  # A mechanism to get ahold of the world state

    sheriff = Sheriff('sheriff', delay=delay)
    sheriff_gun = Gun("sheriff's gun")
    sheriff_gun.move_to(sheriff.right_hand)
    holster = Thing("sheriff's holster")
    holster.move_to(sheriff.body)

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
    glass = Container('glass')
    bottle = Container('bottle')
    bottle.full = True
    glass.move_to(table)
    bottle.move_to(table)

    # Start with the world status
    for obj in stage.objects:
        if not isinstance(obj, Person) and obj.status():
            print(obj.status() + '.', end=" ")

    loop()

def loop():
    """Main story loop, initialized by the delay before the sheriff arrives"""
    print()
    next_actor = stage.actors[0]
    while stage.elapsed_time < MAX_TURNS:
        print()
        print(next_actor.name.upper())
        next_actor = action(next_actor)


if __name__ == '__main__':
    # delay = 0 means the SHERIFF arrives immediately
    # delay = input('Select arrival time for SHERIFF:')
    init(delay=DEFAULT_SHERIFF_DELAY)
