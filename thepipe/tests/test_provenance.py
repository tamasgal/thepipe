#!/usr/bin/env python3
import unittest
from thepipe.provenance import Provenance

class TestProvenance(unittest.TestCase):
    def test_init(self):
        p = Provenance()

    def test_activity(self):
        p = Provenance()
        p.start_activity("test")
        assert p.current_activity.name == "test"
        p.finish_activity()
        assert "test" in [b.name for b in p.backlog]
        assert p.backlog[0].provenance["duration"] > 0

    def test_record_input_output(self):
        p = Provenance()
        p.start_activity("test")
        p.record_input("in.file")
        p.record_output("out.file")
        assert "in.file" == p.current_activity.provenance["input"][0]["url"]
        assert "out.file" == p.current_activity.provenance["output"][0]["url"]

    def test_to_json(self):
        p = Provenance()
        p.start_activity("test")
        p.as_json()

    def test_context_manager(self):
        p = Provenance()
        with p.activity("test"):
            p.record_input("whatever.file")
        assert "test" in [b.name for b in p.backlog]
