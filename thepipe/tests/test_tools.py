# -*- coding: utf-8 -*-
# Filename: test_tools.py
from datetime import datetime, timedelta
from time import sleep
from unittest import TestCase
from mock import MagicMock

from thepipe.tools import Cuckoo, Timer

import numpy as np

__author__ = "Tamas Gal"
__credits__ = []
__license__ = "MIT"
__email__ = "tgal@km3net.de"


class TestCuckoo(TestCase):
    def test_reset_timestamp(self):
        cuckoo = Cuckoo()
        cuckoo.reset()
        delta = datetime.now() - cuckoo.timestamp
        assert delta.total_seconds() > 0

    def test_set_interval_on_init(self):
        cuckoo = Cuckoo(1)
        self.assertEqual(1, cuckoo.interval)

    def test_set_callback(self):
        callback = 1
        cuckoo = Cuckoo(callback=callback)
        self.assertEqual(1, cuckoo.callback)

    def test_callback(self):
        callback = MagicMock()
        message = 'a'
        cuckoo = Cuckoo(callback=callback)
        cuckoo(message)
        callback.assert_called_with(message)

    def test_with_empty_args(self):
        callback = MagicMock()
        cuckoo = Cuckoo(callback=callback)
        cuckoo()
        callback.assert_called_with()

    def test_callback_with_multiple_args(self):
        callback = MagicMock()
        cuckoo = Cuckoo(callback=callback)
        cuckoo(1, 2, 3)
        callback.assert_called_with(1, 2, 3)

    def test_callback_with_multiple_kwargs(self):
        callback = MagicMock()
        cuckoo = Cuckoo(callback=callback)
        cuckoo(a=1, b=2)
        callback.assert_called_with(a=1, b=2)

    def test_callback_with_mixed_args_and_kwargs(self):
        callback = MagicMock()
        cuckoo = Cuckoo(callback=callback)
        cuckoo(1, 2, c=3, d=4)
        callback.assert_called_with(1, 2, c=3, d=4)

    def test_callback_is_not_called_when_interval_not_reached(self):
        callback = MagicMock()
        message = 'a'
        cuckoo = Cuckoo(10, callback)
        cuckoo.reset()
        cuckoo(message)
        self.assertFalse(callback.called)

    def test_callback_is_only_called_when_interval_reached(self):
        callback = MagicMock()
        message = 'a'
        cuckoo = Cuckoo(0.01, callback)
        cuckoo.reset()
        cuckoo(message)
        self.assertFalse(callback.called)
        sleep(0.011)
        cuckoo(message)
        self.assertTrue(callback.called)

    def test_call_sets_timestamp_on_first_call(self):
        cuckoo = Cuckoo()
        cuckoo()
        assert cuckoo.timestamp

    def test_callback_gets_called_on_the_very_first_time(self):
        callback = MagicMock()
        message = 'a'
        cuckoo = Cuckoo(1, callback)
        cuckoo(message)
        self.assertTrue(callback.called)

    def test_call_resets_timestamp_after_interval_reached(self):
        callback = MagicMock()
        message = 'a'
        cuckoo = Cuckoo(0.01, callback)
        cuckoo.reset()
        timestamp1 = cuckoo.timestamp
        print(cuckoo.timestamp)
        self.assertFalse(callback.called)
        sleep(0.011)
        cuckoo(message)
        timestamp2 = cuckoo.timestamp
        print(cuckoo.timestamp)
        self.assertTrue(callback.called)
        assert timestamp1 is not timestamp2

    def test_interval_reached(self):
        cuckoo = Cuckoo(0.01)
        cuckoo.reset()
        self.assertFalse(cuckoo._interval_reached())
        sleep(0.011)
        self.assertTrue(cuckoo._interval_reached())


class TestTimer(TestCase):
    def test_context_manager(self):
        mock = MagicMock()
        with Timer(callback=mock) as t:  # noqa
            pass
        mock.assert_called_once()

    def test_context_manager_calls_with_standard_text(self):
        mock = MagicMock()
        with Timer(callback=mock) as t:  # noqa
            pass
        self.assertTrue(mock.call_args[0][0].startswith("It "))
