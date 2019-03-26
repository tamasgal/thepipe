[![Codacy Badge](https://api.codacy.com/project/badge/Grade/e1c10c17b4224655aa2d9bd61b488589)](https://app.codacy.com/app/tamasgal/thepipe?utm_source=github.com&utm_medium=referral&utm_content=tamasgal/thepipe&utm_campaign=Badge_Grade_Dashboard)
[![Build Status](https://travis-ci.org/tamasgal/thepipe.svg?branch=master)](https://travis-ci.org/tamasgal/thepipe)
[![codecov.io](http://codecov.io/github/tamasgal/thepipe/coverage.svg?branch=master)](http://codecov.io/github/tamasgal/thepipe?branch=master)

# thepipe
A simplistic, general purpose pipeline framework, which can easily be
integrated into existing (analysis) chains and workflows.

## Installation

```shell
pip install thepipe
```

## The Pipeline
Here is a basic example how to create a pipeline, add some modules to it, pass
some parameters and drain the pipeline.

Note that pipeline modules can either be vanilla (univariate) Python functions
or Classes which derive from `thepipe.Module`. 

```python
import thepipe as tp


class AModule(tp.Module):
    def configure(self):
        self.print("Configuring AModule")
        self.max_count = self.get("max_count", default=23)
        self.index = 0

    def process(self, blob):
        self.print("This is cycle #%d" % self.index)
        blob['index'] = self.index
        self.index += 1

        if self.index > self.max_count:
            self.log.critical("That's enough...")
            raise StopIteration
        return blob

    def finish(self):
        self.print("I'm done!")


def a_function_based_module(blob):
    print("Here is the blob:")
    print(blob)
    return blob


pipe = tp.Pipeline()
pipe.attach(AModule, max_count=5)
pipe.attach(a_function_based_module)
pipe.drain()
```

This will produce the following output:

```shell
++ AModule: Configuring AModule
Pipeline and module initialisation took 0.000s (CPU 0.000s).
++ AModule: This is cycle #0
Here is the blob:
Blob (1 entries):
 'index' => 0
++ AModule: This is cycle #1
Here is the blob:
Blob (1 entries):
 'index' => 1
++ AModule: This is cycle #2
Here is the blob:
Blob (1 entries):
 'index' => 2
++ AModule: This is cycle #3
Here is the blob:
Blob (1 entries):
 'index' => 3
++ AModule: This is cycle #4
Here is the blob:
Blob (1 entries):
 'index' => 4
++ AModule: This is cycle #5
CRITICAL ++ AModule: That's enough...
++ AModule: I'm done!
============================================================
5 cycles drained in 0.000793s (CPU 0.000793s). Memory peak: 20.56 MB
  wall  mean: 0.000063s  medi: 0.000057s  min: 0.000045s  max: 0.000106s  std: 0.000022s
  CPU   mean: 0.000065s  medi: 0.000057s  min: 0.000046s  max: 0.000112s  std: 0.000024s
```
