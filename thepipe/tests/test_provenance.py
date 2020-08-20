#!/usr/bin/env python3
import unittest
from thepipe.provenance import Provenance

class TestProvenance(unittest.TestCase):
    def test_init(self):
        p = Provenance()

    def test_start_activity(self):
        p = Provenance()
        p.start_activity("test")
