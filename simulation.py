import random
from collections import deque
from enum import Enum


class Item(Enum):
    A = 'A'
    B = 'B'
    PRODUCT = 'P'
    EMPTY = '_'
    BUSY = '!'


class Conveyor(object):
    """
    Models a conveyor belt of a given length.
    Items are fed onto the belt at a rate of one per tick from the Producer,
    and they fall off the end where they are consumed by the Consumer.
    Conveyor belt advances once space per tick.

    # TODO: Description of busy lock
    """

    def __init__(self, producer, consumer, length=3):
        self.producer = producer
        self.consumer = consumer
        self.len = length
        self.items = [Item.EMPTY] * self.len
        self.busy = False * self.len

    def tick(self):
        # Advance the conveyor
        # Consume what falls off the end
        self.consumer.consume(self.items.pop())
        # Produce something for the start
        self.items.insert(0, self.producer.next())  # consider using a deque instead of a list if items becomes long
        # Sanity check that producer & consumer haven't done too much
        assert (len(self.items) == self.len)
        # Clear all locks ready for workers
        self.busy = False * self.len

    def peek(self, i):
        return self.items[i]

    def take(self, i):
        if self.busy[i]:
            return Item.BUSY
        # Fall through: OK to get something from the belt
        self.busy[i] = True
        item = self.items[i]
        self.items[i] = Item.EMPTY
        return item

    def put(self, item, i):
        """ Puts an item onto the conveyor at position i, returning true on success.
        If there's something already on the conveyor, raises an exception"""

        # TODO: Consider whether Busy and Full should be treated differently?
        if self.busy[i]:
            return False  # "Another worker is already using  conveyor position " + i
        if not self.items[i]:
            return False  # "Conveyor already has an item at position " + i
        # Fall through: OK to put something on the belt
        self.busy[i] = True
        self.items[i] = item
        return True

    def __str__(self):
        return str(self.producer) + '|' +\
               '|'.join(['{:^3}'.format(item.value) for item in self.items]) + '|' \
               + str(self.consumer)


class Workstation(object):
    def __init__(self, conveyor, pos):
        self.conveyor = conveyor
        self.pos = pos

    def peek(self):
        return self.conveyor.peek(self.pos)

    def take(self):
        return self.conveyor.take(self.pos)

    def put(self, item):
        """ Attempt to put item onto the conveyor slot at this station.
        :return True if successful, False if the conveyor was busy or there was another item on the belt. """
        return self.conveyor.put(self.pos, item)


class Worker(object):
    """ A worker with two hands that takes a certain amount of time to assemble a product.
    """

    def __init__(self, workstation, assembly_time=3):
        self.hands = [Item.EMPTY, Item.EMPTY]
        self.station = workstation
        self.assembly_time = assembly_time
        self.steps_remaining = -1  # Init to -1 to represent a non-building worker.

    def __str__(self):
        return '{:1}v{:1}'.format(self.hands[0].value, self.hands[1].value)

    def tick(self):
        # TODO: Would it be clearer to have an explicit state machine?
        # Mutually exclusive actions.
        # It takes one tick to do one of these, so this is effectively a Pythonic switch statement on the current state.

        if self.have_product():
            if self.station.try_put():
                self.hands.remove(Item.PRODUCT)  # If we put it down, remove it from the hands

        elif self.need_a_and_b():  # TODO: Can we combine need a/b, need a, need b in some way?
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

        # check this every time, as we may enter the building state as a result of acquisitions above
        if self.can_build():
            self.tick_build()

    def have_product(self):
        return Item.PRODUCT in self.hands;

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
        return Item.PRODUCT not in self.hands and \
               Item.A in self.hands and \
               Item.B in self.hands

    def tick_build(self):
        if self.steps_remaining == -1:  # We're entering the building state for the first time
            self.steps_remaining = self.assembly_time
        elif self.steps_remaining == 0:  # We're done with building
            # move things around hands (so can_build() will become False)
            self.hands.remove(Item.A)
            self.hands.remove(Item.B)
            self.hands.append(Item.PRODUCT)
            # set sentential value for steps remaining, ready for next time
            self.steps_remaining = -1
        else:  # We're still building, but have less to do now
            self.steps_remaining -= 1


class Producer(object):
    """ Produces items for the head of the conveyor. """

    def next(self):
        return random.choice([Item.A, Item.B, Item.EMPTY])

    def __str__(self):
        return '-> '

class Consumer(object):

    def __init__(self):
        self.output = deque()

    def consume(self, item):
        self.output.appendleft(item)

    def __str__(self):
        return ' -> ' + ','.join([item.value for item in self.output])


class Simulator(object):
    def __init__(self):
        self.producer = Producer()
        self.consumer = Consumer()
        self.conveyor = Conveyor(self.producer, self.consumer)
        self.stations = [Workstation(self.conveyor, i) for i in range(0, self.conveyor.len)]
        self.top_workers = []
        self.bottom_workers = []
        for station in self.stations:
            self.top_workers.append(Worker(station))
            self.bottom_workers.append(Worker(station))

    def tick(self):
        """ Complete one time unit's operations in the simulation. """
        self.conveyor.tick()
        pass

    def run(self, ticks=100):
        """ Run the simulation for the required number of time ticks / steps. """
        for i in range(0, ticks):
            self.tick()
            print(self)
        # TODO: Print results

    def __str__(self):
        return self.str_workers(self.top_workers) + '\n' + \
               str(self.conveyor) + '\n' + \
               self.str_workers(self.bottom_workers)

    @staticmethod
    def str_workers(workers):
        return '    ' + ' '.join([str(worker) for worker in workers])


if __name__ == '__main__':
    s = Simulator()
    s.run(10)
    # c = Conveyor(Producer(), Consumer())
    # for j in range(0, 10):
    #     print(c)
    #     c.tick()
