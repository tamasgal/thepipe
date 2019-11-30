# -*- coding: utf-8 -*-
# Filename: test_core.py
import tempfile
from unittest import TestCase
from mock import MagicMock

from thepipe.core import Pipeline, Module, Blob

__author__ = "Tamas Gal"
__credits__ = []
__license__ = "MIT"
__email__ = "tgal@km3net.de"


class TestPipeline(TestCase):
    """Tests for the main pipeline"""

    def setUp(self):
        self.pl = Pipeline()

    def test_attach(self):
        self.pl.attach(Module, 'module1')
        self.pl.attach(Module, 'module2')
        print([m.name for m in self.pl.modules])
        self.assertEqual('module1', self.pl.modules[0].name)
        self.assertEqual('module2', self.pl.modules[1].name)

    def test_attach_function(self):
        self.pl.attach(lambda x: 1)
        self.pl.attach(lambda x: 2, "Another Lambda")
        self.assertEqual('<lambda>', self.pl.modules[0].name)
        self.assertEqual('Another Lambda', self.pl.modules[1].name)

    def test_drain_calls_each_attached_module(self):
        pl = Pipeline(blob=1)

        func_module_spy = MagicMock()

        def func_module(blob):
            func_module_spy()
            return blob

        pl.attach(Module, 'module1')
        pl.attach(func_module, 'module2')
        pl.attach(Module, 'module3')

        for module in pl.modules:
            print(module)
            if isinstance(module, Module):
                print("normal module, mocking")
                module.process = MagicMock(return_value={})

        n = 3

        pl.drain(n)

        for module in pl.modules:
            try:
                # Regular modules
                self.assertEqual(n, module.process.call_count)
            except AttributeError:
                # Function module
                self.assertEqual(n, func_module_spy.call_count)

    def test_drain_calls_process_method_on_each_attached_module(self):
        pl = Pipeline(blob=1)

        pl.attach(Module, 'module1')
        pl.attach(Module, 'module2')
        pl.attach(Module, 'module3')
        for module in pl.modules:
            module.process = MagicMock(return_value={})
        n = 3
        pl.drain(n)
        for module in pl.modules:
            self.assertEqual(n, module.process.call_count)

    def test_drain_doesnt_call_process_if_blob_is_none(self):
        pl = Pipeline(blob=1)

        pl.attach(Module, 'module1')
        pl.attach(Module, 'module2')
        pl.attach(Module, 'module3')
        pl.modules[0].process = MagicMock(return_value=None)
        pl.modules[1].process = MagicMock(return_value={})
        pl.modules[2].process = MagicMock(return_value={})
        n = 3
        pl.drain(n)
        self.assertEqual(n, pl.modules[0].process.call_count)
        self.assertEqual(0, pl.modules[1].process.call_count)
        self.assertEqual(0, pl.modules[2].process.call_count)

    def test_conditional_module_not_called_if_key_not_in_blob(self):
        pl = Pipeline(blob=1)

        pl.attach(Module, 'module1')
        pl.attach(Module, 'module2', only_if='foo')
        pl.attach(Module, 'module3')

        for module in pl.modules:
            module.process = MagicMock(return_value={})

        pl.drain(1)

        self.assertEqual(1, pl.modules[0].process.call_count)
        self.assertEqual(0, pl.modules[1].process.call_count)
        self.assertEqual(1, pl.modules[2].process.call_count)

    def test_conditional_module_not_called_if_multiple_keys_not_in_blob(self):
        pl = Pipeline(blob=1)

        to_be_called = MagicMock()
        not_to_be_called = MagicMock()

        class DummyPump(Module):
            def process(self, blob):
                blob['foo'] = 1
                blob['bar'] = 2
                return blob

        class ConditionalModule(Module):
            def process(self, blob):
                print(self.only_if)
                print(blob)
                not_to_be_called()
                assert False
                return blob

        class Module1(Module):
            def process(self, blob):
                to_be_called()
                return blob

        class Module2(Module):
            def process(self, blob):
                to_be_called()
                return blob

        pl.attach(DummyPump)
        pl.attach(Module1)
        pl.attach(ConditionalModule, only_if=['foo', 'narf'])
        pl.attach(ConditionalModule, only_if=['narf', 'bar'])
        pl.attach(Module2)

        pl.drain(3)
        assert 6 == to_be_called.call_count
        assert 0 == not_to_be_called.call_count

    def test_conditional_module_called_if_key_in_blob(self):
        pl = Pipeline(blob=1)

        pl.attach(Module, 'module1')
        pl.attach(Module, 'module2', only_if='foo')
        pl.attach(Module, 'module3')

        pl.modules[0].process = MagicMock(return_value={'foo': 23})
        pl.modules[1].process = MagicMock(return_value={})
        pl.modules[2].process = MagicMock(return_value={})

        pl.drain(1)

        self.assertEqual(1, pl.modules[0].process.call_count)
        self.assertEqual(1, pl.modules[1].process.call_count)
        self.assertEqual(1, pl.modules[2].process.call_count)

    def test_conditional_module_called_if_multiple_keys_in_blob(self):
        pl = Pipeline(blob=1)

        pl.attach(Module, 'module1')
        pl.attach(Module, 'module2', only_if=['foo', 'bar'])
        pl.attach(Module, 'module3')

        pl.modules[0].process = MagicMock(return_value={'foo': 23, 'bar': 5})
        pl.modules[1].process = MagicMock(return_value={})
        pl.modules[2].process = MagicMock(return_value={})

        pl.drain(1)

        self.assertEqual(1, pl.modules[0].process.call_count)
        self.assertEqual(1, pl.modules[1].process.call_count)
        self.assertEqual(1, pl.modules[2].process.call_count)

    def test_condition_every(self):
        pl = Pipeline(blob=1)

        pl.attach(Module, 'module1')
        pl.attach(Module, 'module2', every=3)
        pl.attach(Module, 'module3', every=9)
        pl.attach(Module, 'module4', every=10)
        pl.attach(Module, 'module5')

        func_module = MagicMock()
        func_module.__name__ = "MagicMock"
        pl.attach(func_module, 'funcmodule', every=4)

        for module in pl.modules:
            module.process = MagicMock(return_value={})

        pl.drain(9)

        self.assertEqual(9, pl.modules[0].process.call_count)
        self.assertEqual(3, pl.modules[1].process.call_count)
        self.assertEqual(1, pl.modules[2].process.call_count)
        self.assertEqual(0, pl.modules[3].process.call_count)
        self.assertEqual(9, pl.modules[4].process.call_count)
        self.assertEqual(2, func_module.call_count)

    def test_selective_blob_keys(self):
        class DummyPump(Module):
            def process(self, blob):
                return Blob({'a': 1, 'b': 2, 'c': 3})

        class Observer(Module):
            def configure(self):
                self.needed_key = self.require('needed_key')

            def process(self, blob):
                print(blob)
                assert 1 == len(blob)
                assert self.needed_key in blob
                return blob

        pl = Pipeline()
        pl.attach(DummyPump)
        pl.attach(Observer, needed_key='a', blob_keys=['a'])
        pl.attach(Observer, needed_key='b', blob_keys=['b'])
        pl.attach(Observer, needed_key='c', blob_keys=['c'])
        pl.drain(3)

    def test_selective_blob_keys_with_multiple_keys(self):
        n_cycles = 3
        mock_to_be_called = MagicMock()

        class DummyPump(Module):
            def process(self, blob):
                return Blob({'a': 1, 'b': 2, 'c': 3})

        class Observer(Module):
            def process(self, blob):
                assert 2 == len(blob)
                assert 'a' in blob
                assert 'b' in blob
                mock_to_be_called()
                return blob

        class OtherObserver(Module):
            def process(self, blob):
                assert 3 == len(blob)
                assert 'a' in blob
                assert 'b' in blob
                assert 'c' in blob
                mock_to_be_called()
                return blob

        pl = Pipeline()
        pl.attach(DummyPump)
        pl.attach(Observer, blob_keys=['a', 'b'])
        pl.attach(OtherObserver)
        pl.drain(n_cycles)

        assert 2 * n_cycles == mock_to_be_called.call_count

    def test_selective_blob_keys_with_missing_key(self):
        n_cycles = 3
        mock_to_be_called = MagicMock()

        class DummyPump(Module):
            def process(self, blob):
                return Blob({'a': 1, 'b': 2, 'c': 3})

        class Observer(Module):
            def process(self, blob):
                assert 0 == len(blob)
                mock_to_be_called()
                return blob

        pl = Pipeline()
        pl.attach(DummyPump)
        pl.attach(Observer, blob_keys=['x'])
        pl.drain(n_cycles)

        assert n_cycles == mock_to_be_called.call_count

    def test_selective_blob_keys_mutating_the_blob(self):
        class DummyPump(Module):
            def process(self, blob):
                return Blob({'a': 1, 'b': 2, 'c': 3})

        class Mutator(Module):
            def process(self, blob):
                assert 1 == len(blob)
                blob['d'] = 4
                return blob

        class Observer(Module):
            def process(self, blob):
                print(blob)
                assert 4 == len(blob)
                assert 'd' in blob
                assert 4 == blob['d']
                return blob

        pl = Pipeline()
        pl.attach(DummyPump)
        pl.attach(Mutator, needed_key='a', blob_keys=['a'])
        pl.attach(Observer)
        pl.drain(3)

    def test_selective_blob_keys_returning_nothing_doesnt_stop_the_cycle(self):
        mock_to_be_called = MagicMock()

        class DummyPump(Module):
            def process(self, blob):
                return Blob({'a': 1, 'b': 2, 'c': 3})

        class NoStopper(Module):
            def process(self, blob):
                return

        class Observer(Module):
            def process(self, blob):
                mock_to_be_called()
                assert 3 == len(blob)
                return blob

        pl = Pipeline()
        pl.attach(DummyPump)
        pl.attach(NoStopper, blob_keys=['a'])
        pl.attach(Observer)
        pl.drain(3)

        assert 3 == mock_to_be_called.call_count

    def test_drain_calls_function_modules(self):
        pl = Pipeline(blob=1)

        func_module1 = MagicMock()
        func_module2 = MagicMock()
        func_module3 = MagicMock()

        func_module1.__name__ = "MagicMock"
        func_module2.__name__ = "MagicMock"
        func_module3.__name__ = "MagicMock"

        pl.attach(func_module1, 'module1')
        pl.attach(func_module2, 'module2')
        pl.attach(func_module3, 'module3')
        pl.drain(1)
        self.assertEqual(1, pl.modules[0].call_count)
        self.assertEqual(1, pl.modules[1].call_count)
        self.assertEqual(1, pl.modules[2].call_count)

    def test_finish(self):
        out = self.pl.finish()
        assert out is not None

    def test_drain_calls_finish_on_each_attached_module(self):
        self.pl.attach(Module, 'module1')
        self.pl.attach(Module, 'module2')
        self.pl.attach(lambda x: 1, 'func_module')
        for module in self.pl.modules:
            module.finish = MagicMock()
        self.pl.drain(4)
        for module in self.pl.modules:
            if module.name != 'func_module':
                self.assertEqual(1, module.finish.call_count)

    def test_ctrl_c_handling(self):
        pl = Pipeline()
        self.assertFalse(pl._stop)
        pl._handle_ctrl_c()  # first KeyboardInterrupt
        self.assertTrue(pl._stop)
        with self.assertRaises(SystemExit):
            pl._handle_ctrl_c()  # second KeyboardInterrupt

    def test_attached_module_gets_a_parameter_passed_which_is_ignored(self):
        pl = Pipeline()

        log_mock = MagicMock()

        class A(Module):
            def configure(self):
                a = self.get('a')
                self.log = log_mock

        pl.attach(A, a=1, b=2)
        pl.drain(1)

        args, kwargs = log_mock.warning.call_args_list[0]
        assert 'b' == args[1]

    def test_attached_module_gets_multiple_parameters_passed_which_are_ignored(
            self):
        pl = Pipeline()

        log_mock = MagicMock()

        class A(Module):
            def configure(self):
                a = self.get('a')
                self.log = log_mock

        pl.attach(A, a=1, b=2, c=3)
        pl.drain(1)

        args, kwargs = log_mock.warning.call_args_list[0]
        assert 'b, c' == args[1]

    def test_attached_module_does_not_warn_for_reserverd_parameters(self):
        pl = Pipeline()

        log_mock = MagicMock()

        class A(Module):
            def configure(self):
                a = self.get('a')
                self.log = log_mock

        pl.attach(A, a=1, b=2, only_if='a', every=10)
        pl.drain(1)

        args, kwargs = log_mock.warning.call_args_list[0]
        assert 'b' == args[1]

    def test_timeit(TestCase):
        pl = Pipeline(timeit=True)

        class A(Module):
            pass

        pl.attach(A)
        pl.drain(3)


class TestPipelineConfigurationViaFile(TestCase):
    """Auto-configuration of pipelines using TOML files"""

    def test_configuration(self):
        fobj = tempfile.NamedTemporaryFile(delete=True)
        fname = str(fobj.name)
        Pipeline(configfile=fname)
        fobj.close()

    def test_configuration_with_config_for_a_module(self):
        fobj = tempfile.NamedTemporaryFile(delete=True)
        fobj.write(b"[A]\na = 1")
        fobj.flush()
        fname = str(fobj.name)

        class A(Module):
            def configure(self):
                self.a = self.get('a')

            def process(self, blob):
                assert 1 == self.a
                return blob

        pipe = Pipeline(configfile=fname)
        pipe.attach(A)
        pipe.drain(1)

        fobj.close()

    def test_configuration_with_config_for_multiple_modules(self):
        fobj = tempfile.NamedTemporaryFile(delete=True)
        fobj.write(b"[A]\na = 1\nb = 2\n[B]\nc='d'")
        fobj.flush()
        fname = str(fobj.name)

        class A(Module):
            def configure(self):
                self.a = self.get('a')
                self.b = self.get('b')

            def process(self, blob):
                assert 1 == self.a
                assert 2 == self.b
                return blob

        class B(Module):
            def configure(self):
                self.c = self.get('c')

            def process(self, blob):
                assert 'd' == self.c
                return blob

        pipe = Pipeline(configfile=fname)
        pipe.attach(A)
        pipe.attach(B)
        pipe.drain(1)

        fobj.close()

    def test_configuration_with_named_modules(self):
        fobj = tempfile.NamedTemporaryFile(delete=True)
        fobj.write(b"[X]\na = 1\nb = 2\n[Y]\nc='d'")
        fobj.flush()
        fname = str(fobj.name)

        class A(Module):
            def configure(self):
                self.a = self.get('a')
                self.b = self.get('b')

            def process(self, blob):
                assert 1 == self.a
                assert 2 == self.b
                return blob

        class B(Module):
            def configure(self):
                self.c = self.get('c')

            def process(self, blob):
                assert 'd' == self.c
                return blob

        pipe = Pipeline(configfile=fname)
        pipe.attach(A, 'X')
        pipe.attach(B, 'Y')
        pipe.drain(1)

        fobj.close()

    def test_configuration_precedence_over_kwargs(self):
        fobj = tempfile.NamedTemporaryFile(delete=True)
        fobj.write(b"[A]\na = 1\nb = 2")
        fobj.flush()
        fname = str(fobj.name)

        class A(Module):
            def configure(self):
                self.a = self.get('a')
                self.b = self.get('b')

            def process(self, blob):
                assert 1 == self.a
                assert 2 == self.b
                return blob

        pipe = Pipeline(configfile=fname)
        pipe.attach(A, b='foo')
        pipe.drain(1)

        fobj.close()

    def test_configuration_precedence_over_kwargs_when_get_is_used(self):
        fobj = tempfile.NamedTemporaryFile(delete=True)
        fobj.write(b"[A]\na = 1\n b = 2")
        fobj.flush()
        fname = str(fobj.name)

        class A(Module):
            def configure(self):
                self.b = self.get('a')
                self.a = self.get('b')

            def process(self, blob):
                assert 2 == self.a
                return 1 == self.b

        pipe = Pipeline(configfile=fname)
        pipe.attach(A)
        pipe.drain(1)
        fobj.close()

    def test_configuration_precedence_over_kwargs_when_require_is_used(self):
        fobj = tempfile.NamedTemporaryFile(delete=True)
        fobj.write(b"[A]\na = 1\n b = 'abc'")
        fobj.flush()
        fname = str(fobj.name)

        class A(Module):
            def configure(self):
                self.xyz = self.require('a')
                self.b = self.require('b')

            def process(self, blob):
                assert 1 == self.xyz
                return 2 == self.b

        pipe = Pipeline(configfile=fname)
        pipe.attach(A)
        pipe.drain(1)
        fobj.close()

    def test_parameter_with_differing_name(self):
        fobj = tempfile.NamedTemporaryFile(delete=True)
        fobj.write(b"[A]\na = 'abc'")
        fobj.flush()
        fname = str(fobj.name)

        class A(Module):
            def configure(self):
                self.the_a = self.get('a')

            def process(self, blob):
                return 'abc' == self.the_a

        pipe = Pipeline(configfile=fname)
        pipe.attach(A)
        pipe.drain(1)
        fobj.close()

    def test_configuration_variable_extraction(self):
        fobj = tempfile.NamedTemporaryFile(delete=True)
        fobj.write(b"[VARIABLES]\n"
                   b"FOO = 1\n"
                   b"[Narf]\n"
                   b"bar = 'FOO'\n"
                   b"fjoord = 2")
        fobj.flush()
        fname = str(fobj.name)

        pipe = Pipeline(configfile=fname)

        assert 1 == pipe.module_configuration['Narf']['bar']
        assert 2 == pipe.module_configuration['Narf']['fjoord']
        assert 'VARIABLES' not in pipe.module_configuration


class TestModule(TestCase):
    """Tests for the pipeline module"""

    def test_name_can_be_set_on_init(self):
        name = 'foo'
        module = Module(name=name)
        self.assertEqual(name, module.name)

    def test_name_is_read_only(self):
        module = Module(name='foo')
        with self.assertRaises(AttributeError):
            module.name = 'narf'

    def test_process(self):
        blob = Blob()
        module = Module(name='foo')
        processed_blob = module.process(blob)
        self.assertIs(blob, processed_blob)

    def test_add_parameter(self):
        module = Module()
        module.add('foo', 'default')
        self.assertDictEqual({'foo': 'default'}, module.parameters)

    def test_get_parameter(self):
        module = Module()
        module.add('foo', 'default')
        self.assertEqual('default', module.get('foo'))

    def test_default_parameter_value_can_be_overwritten(self):
        class Foo(Module):
            def configure(self):
                self.foo = self.get('foo') or 'default_foo'

        module = Foo()
        self.assertEqual('default_foo', module.foo)
        module = Foo(foo='overwritten')
        self.assertEqual('overwritten', module.foo)

    def test_finish(self):
        module = Module()
        module.finish()


class TestBlob(TestCase):
    """Tests for the blob holding the data"""

    def test_field_can_be_added(self):
        blob = Blob()
        blob['foo'] = 1
        self.assertEqual(1, blob['foo'])

    def test_print_empty_blob(self):
        blob = Blob()
        assert "Empty blob" == str(blob)

    def test_accessing_non_existing_key_raises_keyerror(self):
        blob = Blob()
        with self.assertRaises(KeyError):
            blob['a']

    def test_accessing_non_existing_key_prints_available_keys(self):
        blob = Blob()
        blob['key_a'] = 1
        blob['key_b'] = 2
        blob.log = MagicMock()

        with self.assertRaises(KeyError):
            blob['key_c']

        args, kwargs = blob.log.error.call_args_list[0]
        assert "key_c" in args[0]
        assert "key_a, key_b" in args[0]


class TestServices(TestCase):
    def setUp(self):
        self.pl = Pipeline()

    def test_service(self):
        class Service(Module):
            def configure(self):
                self.expose(23, "foo")
                self.expose(self.whatever, "whatever")

            def whatever(self, x):
                return x * 2

        class UseService(Module):
            def process(self, blob):
                print(self.services)
                assert 23 == self.services["foo"]
                assert 2 == self.services["whatever"](1)

        self.pl.attach(Service)
        self.pl.attach(UseService)
        self.pl.drain(1)

    def test_service_usable_in_configure_when_attached_before(self):
        return

        class Service(Module):
            def configure(self):
                self.expose(23, "foo")
                self.expose(self.whatever, "whatever")

            def whatever(self, x):
                return x * 2

        class UseService(Module):
            def configure(self):
                assert 23 == self.services["foo"]
                assert 2 == self.services["whatever"](1)

        self.pl.attach(Service)
        self.pl.attach(UseService)
        self.pl.drain(1)

    def test_required_service(self):
        class AService(Module):
            def configure(self):
                self.expose(self.a_function, 'a_function')

            def a_function(self, b='c'):
                return b + 'd'

        class AModule(Module):
            def configure(self):
                self.require_service('a_function', why='because')

            def process(self, blob):
                assert 'ed' == self.services['a_function']("e")

        self.pl.attach(AService)
        self.pl.attach(AModule)
        self.pl.drain(2)

    def test_required_service_not_present(self):
        self.pl.log = MagicMock()

        class AModule(Module):
            def configure(self):
                self.require_service('a_function', why='because')

            def process(self, blob):
                assert False  # make sure that process is not called

        self.pl.attach(AModule)
        self.pl.drain(1)

        args, kwargs = self.pl.log.critical.call_args_list[0]
        assert 'a_function' == args[1]

    def test_required_service_not_present_in_multiple_modules(self):
        self.pl.log = MagicMock()

        class AModule(Module):
            def configure(self):
                self.require_service('a_function', why='because')
                self.require_service('b_function', why='because')

            def process(self, blob):
                assert False  # make sure that process is not called

        class BModule(Module):
            def configure(self):
                self.require_service('c_function', why='because')

            def process(self, blob):
                assert False  # make sure that process is not called

        self.pl.attach(AModule)
        self.pl.attach(BModule)
        self.pl.drain(1)

        args, kwargs = self.pl.log.critical.call_args_list[0]
        assert 'a_function, b_function, c_function' == args[1]

    def test_required_service_not_present_but_some_are_present(self):
        self.pl.log = MagicMock()

        class AModule(Module):
            def configure(self):
                self.expose(self.d_function, 'd_function')
                self.require_service('a_function', why='because')
                self.require_service('b_function', why='because')

            def d_function(self):
                pass

            def process(self, blob):
                assert False  # make sure that process is not called

        class BModule(Module):
            def configure(self):
                self.require_service('c_function', why='because')

            def process(self, blob):
                assert False  # make sure that process is not called

        class CModule(Module):
            def configure(self):
                self.require_service('d_function', why='because')

            def process(self, blob):
                assert False  # make sure that process is not called

        self.pl.attach(AModule)
        self.pl.attach(BModule)
        self.pl.attach(CModule)
        self.pl.drain(1)

        args, kwargs = self.pl.log.critical.call_args_list[0]
        assert 'a_function, b_function, c_function' == args[1]
