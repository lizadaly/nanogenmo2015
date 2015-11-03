#!/usr/bin/python
# -*- coding: utf-8 -*-

import inspect
import logging
import random

log = logging.getLogger()

DEFAULT_SHERIFF_DELAY = 20
DEFAULT_NUM_BULLETS = 5
DEFAULT_HEALTH = 5
MAX_SCENES = 350  # ~150 words per scene

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
    current_scene = 0

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
    log.debug("Starting action for actor %s", actor)
    actor.set_starting_location(actor.default_location)
    actor.act()

    stage.elapsed_time += 1

    # Determine who acts next
    next_actor = check_initiative(stage.actors)
    if next_actor.escaped:
        return next_actor

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
    inebriation = 0

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
            #log.debug("+ %s init change for path movement: %s/%s", self.name, HIGH_INITIATIVE, actor_initiative)

        # If they're injured they're pretty mad
        injury_bonus = DEFAULT_HEALTH - self.health
        actor_initiative += injury_bonus
        #log.debug("+ %s init change for injury bonus: %s/%s", self.name, injury_bonus, actor_initiative)

        # They're also more excited if they're almost out of bullets
        if self.get_if_held(Gun):
            bullet_bonus = 10 if self.get_if_held(Gun).num_bullets == 1 else 0
            actor_initiative += bullet_bonus
            #log.debug("- %s init change for bullet bonus: %s/%s", self.name, bullet_bonus, actor_initiative)

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
            cmd, *args = self.queue[0]
            log.debug("Running queued command: %s %s", cmd, args)
            if args:
                cmd(*args)
            else:
                cmd()
            self.queue = self.queue[1:]
            return

        # If there's a target location, try to go there
        if len(self.path) > 0:
            log.debug("Got a path event, walking it")
            next_location = self.path[0]
            if self.go(next_location):
                # If going there was successful, set their new location and drop it from the path
                self.path = self.path[1:]
            return

        # If the enemy is present, try to kill them!
        if self.enemy_is_present():
            # If we don't have the gun, go find it!
            if isinstance(self, Sheriff):  # Lame
                gun = stage.find("sheriff's gun")
            else:
                gun = stage.find("gun")
            if self.get_if_held(gun):
                self.shoot(self.enemy)
            else:
                # Immediately go to the location where the gun is (unless the location is a supporter)
                target_location = gun.location
                self.go(target_location)
                # ...then queue taking the gun and shooting it!
                self.queue.append((self.shoot, self.enemy))
                self.queue.append((self.take, gun))
            return

        # If the enemy is dead, take the money and run
        if self.enemy.is_dead:
            # Blow out the gun if we still have it
            gun = self.get_if_held(Gun)
            holster = self.get_if_held(Holster)
            if gun and not gun.location == holster:
                print("blow out barrel")
                self.queue.append((self.drop, gun, holster))
                return True
            log.debug("*** Trying to get the money")
            money = self.stage.find('money')
            if self.location == money.location:
                return self.take(money)
            # End game! Flee with the money!
            if self.get_if_held('money'):
                self.path = ['door', None]
                self.escaped = True

        # Random behaviors
        weighted_choice = [('drink', 5), ('wander', 3), ('check', 1), ('lean', 1), ('count', 1), ('drop', 1)]
        choice = random.choice([val for val, cnt in weighted_choice for i in range(cnt)])
        log.debug("%s chose to %s", self.name, choice)
        if choice == 'drink':
            # Try to drink from the glass if we're holding it
            glass = stage.find('glass')
            if self.get_if_held('glass'):
                # ...and it's full, just drink from it
                if glass.full:
                    glass.drink(self)
                    return True
                # If not, try to pour a glass from the bottle
                else:
                    bottle = stage.find('bottle')
                    if self.get_if_held(bottle):
                        bottle.pour(glass)
                        # Be sure to add queued events in reverse order because queues
                        self.queue.append((glass.drink, self))
                        self.queue.append((self.take, glass))
                        return True
                    # If we don't have the bottle and can reach it, take it and
                    # then queue pouring it and drinking from it
                    else:
                        if self.can_reach_obj(bottle):
                            self.take(bottle)
                            self.queue.append((glass.drink, self))
                            self.queue.append((self.take, glass))
                            self.queue.append((bottle.pour, glass))
                            return True
            # If we don't have the glass, try to get it
            else:
                if self.can_reach_obj(glass):
                    self.take(glass)
                    return True
        elif choice == 'wander':
            return self.go_to_random_location()
        elif choice == 'check':
            if self.get_if_held(Gun):
                print("check gun")
                return True
        elif choice == 'count':
            if self.can_reach_obj(stage.find('money')):
                print("count money")
                return True
        elif choice == 'lean':
            if self.location == stage.find('window'):
                print('lean on window and look')
                return True
        elif choice == 'drop':  # Drop a random object that isn't the gun
            obj = self.get_held_obj(self.right_hand)
            if obj and not isinstance(obj, Gun):
                self.drop(obj, self.location)
                return True
            else:
                obj = self.get_held_obj(self.left_hand)
                if obj and not isinstance(obj, Gun):
                    self.drop(obj, self.location)
                    return True
        # If we fell threw and did nothing, try again
        return self.act()

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
        free_hand = self.free_hand()
        if free_hand:
            print("pick up the {} with the {}".format(obj, free_hand))
            obj.move_to(free_hand)
            return True
        else:
            # Drop the thing in a random hand and queue picking up the thing
            self.drop(self.get_held_obj(random.choice((self.right_hand, self.left_hand))), self.location)
            self.queue.append((self.take, obj))


    def go_to_random_location(self):
        """Randomly go to a location that isn't the current one"""
        location = random.choice([place for place in stage.places if place != self.location and not isinstance(place, Door)])
        self.go(location)

    def enemy_is_present(self):
        """Is the enemy visible and suitably shootable?"""
        return self.enemy.location != None and self.enemy.is_alive

    def shoot(self, target, aimed=False):
        """Shoot first, ask questions never"""
        gun = self.get_if_held(Gun)
        if gun:
            # Usually we'll aim and then fire, sometimes we'll just fire
            if not aimed:
                if random.randint(0, 5) > 1:
                    print("aim")
                    self.queue.append((self.shoot, target, True))
                    return False
            print("fire")
            log.debug("%s is trying to shoot %s", self.name, target.name)
            hit_weight = self.starting_hit_weight()
            if gun.num_bullets == 1:
                hit_weight += 1
            if self.health < DEFAULT_HEALTH:
                hit_weight += 1

            weighted_hit_or_miss = [('miss', 3), ('nick', 3 * hit_weight), ('hit', 1 * hit_weight)]
            hit_or_nick = random.choice([val for val, cnt in weighted_hit_or_miss for i in range(cnt)])
            print(GUN_DAMAGE[hit_or_nick]['message'].format(target.name))
            target.health += GUN_DAMAGE[hit_or_nick]['health']
            gun.num_bullets -= 1
            return True

    def starting_hit_weight(self):
        """Return a state-dependent starting weight that can increase or decrease the likelihood of
        the actor making a successful shot."""
        return 1

    def go(self, location):
        """Try to move to the next location. If that location can be opened, like a door, open it first.
        Otherwise, set the new location.  If `location` is a string, find the
        name of that location in the world."""

        if isinstance(location, str):
            location = self.stage.find(location)

        log.debug("Trying to go to next location %s", location)

        if location.is_openable and not location.is_open:
            location.open()
            return False

        if location.is_openable and location.is_open:
            print("go through {}".format(location))
            self.queue.append((location.close,))
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
            # If not, try to find the named object
            obj = self.stage.find(obj_name)
        else:
            obj = obj_name
        if obj.location in self.parts:
            return obj

    def get_held_obj(self, part):
        """Get the object held by a given body part. Returns None if the body part isn't holding anything"""
        for obj in stage.objects:
            if obj.location == part:
                return obj

    def free_hand(self):
        """Return the hand that isn't holding anything"""
        right_free = True
        left_free = True
        for obj in stage.objects:
            if obj.location == self.right_hand:
                right_free = False
            elif obj.location == self.left_hand:
                left_free = False
        if right_free:
            return self.right_hand
        if left_free:
            return self.left_hand

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
            print("put {} {} {}".format(obj.name, target.preposition, target.name))
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

    def starting_hit_weight(self):
        """The Robber (but _not_ the Sheriff) is a better shot if he's drunk"""
        return self.inebriation + 2

class Sheriff(Person):
    """The Sheriff wants to kill the Robber and leave with the money. He does not get a drink bonus and arrives
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

    def starting_hit_weight(self):
        """The Sheriff (but _not_ the Robber) is a better shot if he's injured"""
        weight = 1
        if self.health < DEFAULT_HEALTH:
            weight += 3
        return weight

class Gun(Thing):
    """A Gun is an object with a distinct property of being shootable and having a number of bullets"""
    num_bullets = 0
    def __init__(self, name):
        super(Gun, self).__init__(name)
        self.num_bullets = DEFAULT_NUM_BULLETS

class Holster(Thing):
    def __init__(self, name, preposition='in'):
        super(Holster, self).__init__(name, preposition=preposition)

class Container(Thing):
    """A Container is a vessel that can contain a thing (whisky)"""
    volume = 0

    def __init__(self, name):
        super(Container, self).__init__(name)

    @property
    def full(self):
        """A container is 'full' if it contains any volume"""

        return self.volume > 0
    def pour(self, new_container):
        """Pouring from a full container into an empty container makes
        the other container full. It doesn't make the source container
        any less full because magic. If the source container is empty,
        this is a no-op. Returns True if the pour succeeded."""
        if self.full:
            print("pour")
            new_container.volume = 3
            return True

    def drink(self, actor):
        """Drinking from a full container changes the inebriation status
        of the actor. Drinking from an empty glass has no effect.
        Returns True if the drink succeeded."""
        if self.full:
            print("take a drink from {}".format(self))
            actor.inebriation += 1
            self.volume -= 1
            return True

def init(delay):
    """Initialize the starting conditions"""

    # Humans
    robber = Robber('robber')
    robber_gun = Gun('gun')
    robber_gun.move_to(robber.right_hand)
    money = Thing('money')
    money.move_to(robber.left_hand)
    robber_holster = Holster('holster')
    robber_holster.move_to(robber.body)
    robber.stage = stage  # A mechanism to get ahold of the world state

    sheriff = Sheriff('sheriff', delay=delay)
    sheriff_gun = Gun("sheriff's gun")
    sheriff_gun.move_to(sheriff.right_hand)
    holster = Holster("sheriff's holster")
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
    bottle.volume = 10
    glass.move_to(table)
    bottle.move_to(table)

    stage.current_scene += 1

    loop()

def loop():
    """Main story loop, initialized by the delay before the sheriff arrives"""
    # Start with the world status
    print ("\nAct 1 Scene {}\n\n".format(stage.current_scene))
    for obj in stage.objects:
        if not isinstance(obj, Person) and obj.status():
            print(obj.status() + '.', end=" ")

    print()
    next_actor = stage.actors[0]
    while True:
        print()
        print(next_actor.name.upper())

        next_actor = action(next_actor)
        if next_actor.escaped:
            print("CURTAIN")
            stage.objects = []
            stage.places = []
            break

if __name__ == '__main__':
    delay = input('Select arrival time for SHERIFF or ENTER for default: ') or DEFAULT_SHERIFF_DELAY
    print("""

SAGA III
An Original Play
by
A Computer """)

    for i in range(0, MAX_SCENES):
        init(delay=int(delay))
