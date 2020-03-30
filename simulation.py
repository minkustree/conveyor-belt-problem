"""
Factory production line simulation
Andy Clark - 2020-03-30

The production line is modelled within the Simulator.
A Conveyor moves one step with each tick, and each space on the conveyor can hold one Item (or be empty)
A Producer adds an Item  (or empty space) to the left of the Conveyor (position 0) with each tick.
A Consumer receives the item which falls off the conveyor with each tick, and is responsible for tallying how many of
each item makes it to the end of the conveyor.

Each space on the Conveyor is associated with a Workstation. Only one action (putting or taking from the space) is
permitted at each workstation on each tick.

There are two Workers assigned to each workstation, notionally on the 'top'and 'bottom' sides of the conveyor belt.
Workers pick up components, and place products on the belt via the workstation. When they have the components they need
to build a product, they spend a number of ticks doing so before the product is ready. Workers have two 'hands' in which
they hold components or finished products.
"""

import random
from collections import deque, Counter
from enum import Enum


class Item(Enum):
    """ Something that can be on the conveyor belt (including an empty space) """
    A = 'A'
    B = 'B'
    PRODUCT = 'P'
    EMPTY = '_'


class Conveyor(object):
    """
    Models a conveyor belt of a given length.
    Items are fed onto the belt at a rate of one per tick from the Producer,
    and they fall off the end where they are consumed by the Consumer.
    Conveyor belt advances once space per tick.
    Spaces on the conveyor are indexed from 0, with 0 being the space that new items are placed on from the producer,
    and len-1 is the last space before the conveyor ends.
    """

    def __init__(self, producer, consumer, length=3):
        self.producer = producer
        self.consumer = consumer
        self.len = length
        self.items = deque([Item.EMPTY] * self.len)  # Double-ended queue avoids delays if length is large

    def tick(self):
        """ Advance the conveyor, producing and consuming items at either end"""
        # Consume what falls off the end
        self.consumer.consume(self.items.pop())
        # Produce something for the start
        self.items.insert(0, self.producer.next())  # consider using a deque instead of a list if items becomes long
        # Sanity check that producer & consumer haven't done too much
        assert (len(self.items) == self.len)

    def peek(self, i):
        """ Return  the item at position i on the conveyor without removing it. """
        return self.items[i]

    def take(self, i):
        """ Take an item from the belt, leaving it empty.
        Returns the item taken, or Item.EMPTY if there was nothing on the belt """
        item = self.items[i]
        self.items[i] = Item.EMPTY
        return item

    def put(self, i, item):
        """ Puts an item onto the conveyor at position i, returning true on success.
        If there's something already on the conveyor, returns false"""
        if self.items[i] is not Item.EMPTY:
            return False  # "Conveyor already has an item at position " + i
        # OK to put something on the belt
        self.items[i] = item
        return True

    def __str__(self):
        return str(self.producer) + '|' + \
               '|'.join(['{:^3}'.format(item.value) for item in self.items]) + '|' \
               + str(self.consumer)


class Workstation(object):
    """ Controlls shared access to a conveyor position. Only the first access per tick is allowed."""
    def __init__(self, conveyor, pos):
        self.conveyor = conveyor
        self.pos = pos
        self.busy = False

    def tick(self):
        self.busy = False

    def peek(self):
        return self.conveyor.peek(self.pos)

    def take(self):
        """ Returns the item on the conveyor at this workstation, or None if the workstation is busy. """
        if self.busy:
            return None
        self.busy = True
        return self.conveyor.take(self.pos)

    def put(self, item):
        """ Attempt to put item onto the conveyor slot at this station.
        :return True if successful, False if the conveyor was busy or there was another item on the belt. """
        if self.busy:
            return False
        put_success = self.conveyor.put(self.pos, item)
        if put_success:
            # We're only busy if the put succeeded. There may have been something else on the belt
            self.busy = True
        return put_success


class Worker(object):
    """
    A worker with two hands that takes a certain amount of time to assemble a product.
    """

    def __init__(self, workstation, assembly_time=3):
        self.hands = []  # Normally two items, but could generalise to more
        self.station = workstation
        self.assembly_time = assembly_time
        self.steps_remaining = 0  # A '0' represents not building the product on this tick

    def tick(self):
        """
        Process the next action for a worker in this time step.
        Assumes that:
         * a worker can can hold a product in their hand while gathering a component in another.
         * a worker can complete the product assembly and put it back on the conveyor on the 4th step after picking up
         * a worker
        """

        # Product in hand?
        if self.have_product():
            if self.station.put(Item.PRODUCT):
                self.hands.remove(Item.PRODUCT)  # If we put it down, remove it from the hands
        # Components needed?
        elif self.need_a_and_b():  # TODO: Can we make these steps simpler without loss of clarity?
            if self.station.peek() in [Item.A, Item.B]:
                self.hands.append(self.station.take())
            # else didn't get it this time. wait.
        elif self.need_a():
            if self.station.peek() in [Item.A]:
                self.hands.append(self.station.take())
            # else didn't get it this time. wait.
        elif self.need_b():
            if self.station.peek() in [Item.B]:
                self.hands.append(self.station.take())
            # else didn't get it this time. wait.
        # Building ?
        # check this every time, as we may enter the building state as a result of acquisitions above
        if self.can_build():
            self.tick_build()

    def tick_build(self):
        """
        Checks to see if we can enter a build sequence, processing the next step in that sequence if
        appropriate.
        """
        if self.steps_remaining == 0:  # We're entering the building sequence for the first time on this tick
            self.steps_remaining = self.assembly_time
        elif self.steps_remaining == 1:  # This tick is the last step - complete the build
            # move things around hands (so can_build() will become False)
            self.hands.remove(Item.A)
            self.hands.remove(Item.B)
            self.hands.append(Item.PRODUCT)
            # set sentential value for steps remaining, ready for next time
            self.steps_remaining = 0
        else:  # We're still building, but have less to do now
            self.steps_remaining -= 1

    def have_product(self):
        """ Returns true if the worker has a product in their hands"""
        return Item.PRODUCT in self.hands

    def need_a_and_b(self):
        """ Returns true if the worker needs both A and B to continue, and has no product  """
        return self.need_a() and self.need_b()

    def need_a(self):
        """ Returns true if the worker just needs A to continue """
        return Item.A not in self.hands

    def need_b(self):
        """ Returns true if the worker just needs B to continue """
        return Item.B not in self.hands

    def can_build(self):
        """ Returns true if the worker has all they need to build, and hasn't got a finished product in hand"""
        return Item.PRODUCT not in self.hands and \
               Item.A in self.hands and \
               Item.B in self.hands

    def __str__(self):
        state = 'v'
        left = right = '_'
        if self.steps_remaining > 0:
            state = str(self.steps_remaining)
        if len(self.hands) >= 2:
            right = self.hands[1].value
        if len(self.hands) >= 1:
            left = self.hands[0].value
        return '{:1}{:1}{:1}'.format(left, state, right)


class RandomProducer(object):
    """ Produces items for the head of the conveyor.

    Keeps track of the next item to be produced, only for pretty print purposes
    """

    def __init__(self):
        self.next_item = self._random_next()

    def next(self):
        result = self.next_item
        self.next_item = self._random_next()
        return result

    @staticmethod
    def _random_next():
        return random.choice([Item.A, Item.B, Item.EMPTY])

    def __str__(self):
        return '{}> '.format(self.next_item.value)


# class FixedProducer(object):
#     """
#     Produces items for the head of the conveyor from a fixed list.
#     Useful for testing
#     """
#
#     def __init__(self):
#         self.items = [Item.B, Item.A]
#
#     def next(self):
#         if self.items:
#             return self.items.pop()
#         return Item.EMPTY
#
#     def __str__(self):
#         return '-> '


class Consumer(object):
    """
    Consumes items that fall off the end of the conveyor.
    Counts how many items of each type are seen.
    """

    def __init__(self):
        self.output = deque()
        self.counter = Counter()

    def consume(self, item):
        self.output.appendleft(item)
        self.counter[item] += 1

    def get_count(self):
        return self.counter

    def __str__(self):
        return ' -> ' + ','.join([item.value for item in self.output])


class Simulator(object):
    def __init__(self, show_steps=False):
        # TODO: Expose these as optional arguments for easier mocking
        self.producer = RandomProducer()
        self.consumer = Consumer()
        self.conveyor = Conveyor(self.producer, self.consumer)
        self.stations = [Workstation(self.conveyor, i) for i in range(0, self.conveyor.len)]
        self.top_workers = []
        self.bottom_workers = []
        for station in self.stations:
            self.top_workers.append(Worker(station))
            self.bottom_workers.append(Worker(station))

        self.show_steps = show_steps

    def tick(self):
        """ Complete one time unit's worth of operations in the simulation. """
        # advance the conveyor
        self.conveyor.tick()
        # reset workstation busy states
        for station in self.stations:
            station.tick()
        # process worker actions
        # Note, the order in which the workers are processed could have an effect on the efficiency of the algorithm
        for top_worker, bottom_worker in zip(self.top_workers, self.bottom_workers):
            # TODO: Consider randomising which of these goes first to avoid starvation ?
            top_worker.tick()
            bottom_worker.tick()

    def run(self, ticks=100):
        print("Running simulator with {} steps.\n".format(ticks))
        """ Run the simulation for the required number of time ticks / steps. """
        for i in range(0, ticks):
            self.tick()
            if self.show_steps:
                print("Step {}:".format(i))
                print(self)

    def print_results(self):
        print("Results:")
        print("  Finished products: {}".format(self.consumer.counter[Item.PRODUCT]))
        print("  Unused components. A: {}, B: {}".format(self.consumer.counter[Item.A], self.consumer.counter[Item.B]))

    def __str__(self):
        return self.str_workers(self.top_workers) + '\n' + \
               str(self.conveyor) + '\n' + \
               self.str_workers(self.bottom_workers)

    @staticmethod
    def str_workers(workers):
        return '    ' + ' '.join([str(worker) for worker in workers])


if __name__ == '__main__':
    s = Simulator(show_steps=False)
    s.run(100)
    s.print_results()
