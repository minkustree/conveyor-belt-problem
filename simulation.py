class Simulator(object):
    def tick(self):
        """ Complete one time unit's operations in the simulation. """
        pass

    def run(self, ticks=100):
        """ Run the simulation for the required number of time ticks / steps. """
        for i in range(0, ticks):
            self.tick()
        # TODO: Print results


class Conveyor(object):
    """
    Models a conveyor belt of a given length.
    Items are fed onto the belt at a rate of one per tick from the Producer,
    and they fall off the end where they are consumed by the Consumer.
    Conveyor belt advances once space per tick.
    """

    EMPTY = ''

    def __init__(self, producer, consumer, length=3):
        self.producer = producer
        self.consumer = consumer
        self.len = length
        self.items = [Conveyor.EMPTY] * self.len

    def tick(self):
        # Advance the conveyor:
        # Consume what falls off the end
        self.consumer.consume(self.items.pop())
        # Produce something for the start
        self.items.insert(0, self.producer.next())  # consider using a deque instead of a list if items becomes long
        assert (len(self.items) == self.len)

    def peek(self, i):
        return self.items[i]

    def get(self, i):
        item = self.items[i]
        self.items[i] = Conveyor.EMPTY

    def put(self, item, i):
        """ Puts an item onto the conveyor at position i, returning true on success.
        If there's something already on the conveyor, raises an exception"""
        if not self.items[i]:
            raise Exception("Conveyor already has an item at position " + i)
        self.items[i] = item

    def __str__(self):
        return '|'.join(['{:4}'.format(item) for item in self.items])


class Producer(object):
    def next(self):
        return "A"


class Consumer(object):
    def consume(self, item):
        print("Output: " + item)


if __name__ == '__main__':
    c = Conveyor(Producer(), Consumer())
    print(c)
    c.tick()
    print(c)
    c.tick()
    print(c)
    c.tick()
    print(c)
    c.tick()
    print(c)
