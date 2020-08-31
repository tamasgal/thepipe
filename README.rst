thepipe
=======

.. image:: https://readthedocs.org/projects/thepipe/badge/?version=latest
    :target: https://thepipe.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://api.codacy.com/project/badge/Grade/20a35727ae364e08845b60bdeb4b233a
    :alt: Codacy Badge
    :target: https://www.codacy.com/app/tamasgal/thepipe?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=tamasgal/thepipe&amp;utm_campaign=Badge_Grade

.. image:: https://travis-ci.org/tamasgal/thepipe.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/tamasgal/thepipe

.. image:: http://codecov.io/github/tamasgal/thepipe/coverage.svg?branch=master
    :alt: Test-coverage
    :target: http://codecov.io/github/tamasgal/thepipe?branch=master

.. image:: https://img.shields.io/pypi/v/thepipe.svg?style=flat
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/thepipe

A simplistic, general purpose pipeline framework, which can easily be
integrated into existing (analysis) chains and workflows.

Installation
------------
``thepipe`` can be installed via ``pip``::

    pip install thepipe

Features
--------

- Easy to use interface and integration into existing workflows
- Automatic provenance tracking (set ``Provenance().outfile`` to dump it upon
  program termination)
- Modules can be either subclasses of ``Module`` or bare python functions
- Data is passed via a simple Python dictionary from module to module (wrapped
  in a class called ``Blob`` which adds some visual candy and error reporting)
- Integrated hierarchical logging system
- Colour coded log and print messages (``self.log()`` and ``self.cprint()`` in
  ``Modules``)
- Performance statistics for the whole pipeline and each module individually
- Clean exit when interrupting the pipeline with CTRL+C

The Pipeline
------------

Here is a basic example how to create a pipeline, add some modules to it, pass
some parameters and drain the pipeline.

Note that pipeline modules can either be vanilla (univariate) Python functions
or Classes which derive from ``thepipe.Module``.

.. code-block:: python

    import thepipe as tp


    class AModule(tp.Module):
        def configure(self):
            self.cprint("Configuring AModule")
            self.max_count = self.get("max_count", default=23)
            self.index = 0

        def process(self, blob):
            self.cprint("This is cycle #%d" % self.index)
            blob['index'] = self.index
            self.index += 1

            if self.index > self.max_count:
                self.log.critical("That's enough...")
                raise StopIteration
            return blob

        def finish(self):
            self.cprint("I'm done!")


    def a_function_based_module(blob):
        print("Here is the blob:")
        print(blob)
        return blob


    pipe = tp.Pipeline()
    pipe.attach(AModule, max_count=5)  # pass any parameters to the module
    pipe.attach(a_function_based_module)
    pipe.drain()  # without arguments it will drain until a StopIteration is raised

This will produce the following output:

.. code-block:: shell

    2020-05-26 12:43:12 ++ AModule: Configuring AModule
    Pipeline and module initialisation took 0.001s (CPU 0.001s).
    2020-05-26 12:43:12 ++ AModule: This is cycle #0
    Here is the blob:
    Blob (1 entries):
    'index' => 0
    2020-05-26 12:43:12 ++ AModule: This is cycle #1
    Here is the blob:
    Blob (1 entries):
    'index' => 1
    2020-05-26 12:43:12 ++ AModule: This is cycle #2
    Here is the blob:
    Blob (1 entries):
    'index' => 2
    2020-05-26 12:43:12 ++ AModule: This is cycle #3
    Here is the blob:
    Blob (1 entries):
    'index' => 3
    2020-05-26 12:43:12 ++ AModule: This is cycle #4
    Here is the blob:
    Blob (1 entries):
    'index' => 4
    2020-05-26 12:43:12 ++ AModule: This is cycle #5
    2020-05-26 12:43:12 CRITICAL ++ AModule: That's enough...
    2020-05-26 12:43:12 ++ AModule: I'm done!
    ============================================================
    5 cycles drained in 0.001284s (CPU 0.001475s). Memory peak: 27.01 MB
    wall  mean: 0.000070s  medi: 0.000052s  min: 0.000042s  max: 0.000122s  std: 0.000031s
    CPU   mean: 0.000070s  medi: 0.000052s  min: 0.000042s  max: 0.000124s  std: 0.000032s
