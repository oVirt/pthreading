# pthreading

## Overview

Reimplement threading.Lock, RLock, and Condition with libpthread.

The pthreading module provides Lock, RLock, and Condition
synchronization objects compatible with Python native threading module.
The implementation, however, is based on POSIX thread library as
delivered by the libpthread. The provided objects are designed to be a
drop-in replacement for their respective threading counterpart.

Take a look at threading.py of Python 2. Notice that Condition.wait()
wakes 20 times a second and checks if the event has been set. This CPU
hogging has been fixed in Python 3, but is not expected to change during
Python 2 lifetime.

## Usage

To avoid this waste of resources, put in your main module:

```python
import pthreading
pthreading.monkey_patch()
```

This would hack the Linux-native threading module, and make it use
Linux-native POSIX synchronization objects.

## Hacking

To perform pep8 check and run the tests:

    tox

To run only pep8 or the tests, specify the tox env:

    tox -e test

For more control over the tests, use py.test directly. In this example
we are running only the Event tests, using verbose mode, and aborting on
the first failure:

    py.test -k TestEvent -vx tests.py

In this example we run the tests and create a coverage report in html
format:

    py.test --cov pthreading --cov pthread --cov-report html tests.py

To view the coverage report, open htmlcov/index.html.

For more info on py.test, please run py.test -h.

## Acknowledgements

The pthreading code was originally written as part of Vdsm by Cyril
Plisko, Saggi Mizrahi and others. For questions, comments and patches
please contact vdsm-devel.
