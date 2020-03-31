from unittest import TestCase
from unittest.mock import Mock
from simulation import *


class TestWorkstation(TestCase):
    def setUp(self) -> None:
        self.mk_conveyor = Mock(spec=Conveyor)
        self.mk_conveyor.take.return_value = Item.A
        self.mk_conveyor.put.return_value = True

        self.w = Workstation(self.mk_conveyor, 0)
        pass

    def test_take(self):
        self.assertEqual(self.w.take(), Item.A)
        # subsequent takes are 'busy'
        self.assertIsNone(self.w.take())
        # subsequent put is busy
        self.assertFalse(self.w.put(Item.A))
        # tick clears busy
        self.w.tick()
        self.assertEqual(self.w.take(), Item.A)

    def test_put(self):
        # self.assertIsNone(self.c.item)
        self.assertTrue(self.w.put(Item.B))
        self.mk_conveyor.put.assert_called_with(Item.B, 0)
        self.mk_conveyor.put.reset_mock()

        # Subsequent put is busy
        self.assertFalse(self.w.put(Item.A))
        self.mk_conveyor.put.assert_not_called()

        # Subsequent take is busy
        self.assertIsNone(self.w.take())
        # tick clears busy
        self.w.tick()
        self.assertTrue(self.w.put(Item.B))
        self.mk_conveyor.put.assert_called_with(Item.B, 0)


class TestWorker(TestCase):

    def setUp(self) -> None:
        self.station = Mock(spec=Workstation)
        self.w = Worker(self.station)
        pass

    def _set_conveyor_item(self, item):
        self.station.peek.return_value = item
        self.station.take.return_value = item

    def assertStatesTrue(self, *true_fns):
        state_fns = [self.w.need_a_and_b, self.w.need_a, self.w.need_b, self.w.can_build, self.w.have_product]
        for true_fn in true_fns:
            self.assertTrue(true_fn(), "{} state function was unexpectedly False".format(true_fn.__name__))
        for false_fn in [fn for fn in state_fns if fn not in true_fns]:
            self.assertFalse(false_fn(), "{} state function was unexpectedly True".format(false_fn.__name__))

    def test_correct_state_empty_hand(self):
        self.w.hands = []  # force empty hands
        self.assertStatesTrue(self.w.need_a_and_b, self.w.need_a, self.w.need_b)

    def test_correct_state_a_in_hand(self):
        self.w.hands = [Item.A]
        self.assertStatesTrue(self.w.need_b)

    def test_correct_state_b_in_hand(self):
        self.w.hands = [Item.B]
        self.assertStatesTrue(self.w.need_a)

    def test_correct_state_a_and_b_in_hand(self):
        self.w.hands = [Item.A, Item.B]
        self.assertStatesTrue(self.w.can_build)

    def test_correct_state_product_in_hand(self):
        self.w.hands = [Item.PRODUCT]
        self.assertStatesTrue(self.w.have_product, self.w.need_a_and_b, self.w.need_a, self.w.need_b)

    def test_empty_hands_grabs_a(self):
        # force empty hands
        self.w.hands = []

        # Mock up Conveyor so that it has Item.A on belt
        self._set_conveyor_item(Item.A)
        # tick
        self.w.tick()
        # check that A is in hands
        self.assertListEqual(self.w.hands, [Item.A])

    def test_empty_hands_grabs_b(self):
        # force empty hands
        self.w.hands = []

        # Mock up Conveyor so that it has Item.B on belt
        self._set_conveyor_item(Item.B)
        # tick
        self.w.tick()
        # check that B is in hands
        self.assertListEqual(self.w.hands, [Item.B])

    def test_empty_hands_doesnt_grab_product(self):
        # force empty hands
        self.w.hands = []

        # Mock up Conveyor so that it has Item.PRODUCT on belt
        self._set_conveyor_item(Item.PRODUCT)
        # tick
        self.w.tick()
        # check that B is in hands
        self.assertListEqual(self.w.hands, [])

    def test_empty_hands_doesnt_grab_empty(self):
        self.w.hands = []
        self._set_conveyor_item(Item.EMPTY)
        self.w.tick()
        self.assertListEqual(self.w.hands, [])

    def test_hands_with_a_grabs_b_only(self):
        self.w.hands = [Item.A]
        self._set_conveyor_item(Item.EMPTY)
        self.w.tick()
        self.assertListEqual(self.w.hands, [Item.A])

        self._set_conveyor_item(Item.PRODUCT)
        self.w.tick()
        self.assertListEqual(self.w.hands, [Item.A])

        self._set_conveyor_item(Item.A)
        self.w.tick()
        self.assertListEqual(self.w.hands, [Item.A])

        self._set_conveyor_item(Item.B)
        self.w.tick()
        self.assertListEqual(self.w.hands, [Item.A, Item.B])

    def test_hands_with_b_grabs_a_only(self):
        self.w.hands = [Item.B]
        self._set_conveyor_item(Item.EMPTY)
        self.w.tick()
        self.assertListEqual(self.w.hands, [Item.B])

        self._set_conveyor_item(Item.PRODUCT)
        self.w.tick()
        self.assertListEqual(self.w.hands, [Item.B])

        self._set_conveyor_item(Item.B)
        self.w.tick()
        self.assertListEqual(self.w.hands, [Item.B])

        self._set_conveyor_item(Item.A)
        self.w.tick()
        self.assertListEqual(self.w.hands, [Item.B, Item.A])

    def test_hands_with_both_starts_production(self):
        self.w.hands = [Item.A]
        self._set_conveyor_item(Item.B)
        self.w.tick()  # production started on this tick as item B was accepted.
        self.station.put.assert_not_called()

        self.station.peek.return_value = Item.EMPTY
        self.station.take.reset_mock()

        self.w.tick()  # 1st subsequent slot
        self.station.put.assert_not_called()
        self.station.take.assert_not_called()

        self.w.tick()  # 2nd subsequent slot
        self.station.put.assert_not_called()
        self.station.take.assert_not_called()

        self.w.tick()  # 3rd subsequent slot
        self.station.put.assert_not_called()
        self.station.take.assert_not_called()

        self.w.tick()  # 4th subsequent slot - product should be placed on the conveyor here
        self.station.put.assert_called_with(Item.PRODUCT)
        self.station.take.assert_not_called()
