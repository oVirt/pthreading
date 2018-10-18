#
# Copyright 2011-2017 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#

"""Reimplement threading.Lock, RLock and Condition with libpthread

The pthreading module provides Lock and Condition synchronization
objects compatible with Python native threading module.
The implementation, however, is based on POSIX thread library as delivered
by the libpthread. Lock and Condition are designed to be a drop-in
replacement for their respective threading counterpart.

Take a look at threading.py of Python 2. Notice that Condition.wait() wakes 20
times a second and checks if the event has been set. This CPU hogging has been
fixed in Python 3, but is not expected to change during Python 2 lifetime.

To avoid this waste of resources, put in your main module::

    import pthreading
    pthreading monkey_patch()

This would hack the Linux-native threading module, and make it use Linux-native
POSIX synchronization objects.

Note: you must invoke pthreading.monkey_patch before importing the thread and
threading modules. If these modules are already imported, monkey_patch will
raise a RuntimeError.

The pthreading code was originally written as part of
`Vdsm <http://wiki.ovirt.org/wiki/Vdsm>`_ by Cyril Plisko, Saggi Mizrahi and
others. For questions, comments and patches please contact `devel@ovirt
<mailto:devel@ovirt.org>`_.
"""

import time
import errno
import os
import sys

import pthread


__version__ = "0.1.6"


class _Lock(pthread.Mutex):
    """
    _Lock class mimics Python native threading.Lock() API on top of
    the POSIX thread mutex synchronization primitive.
    """
    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def acquire(self, blocking=True):

        rc = self.lock() if blocking else self.trylock()

        if rc == 0:
            return True
        elif rc == errno.EBUSY:
            return False
        else:
            raise OSError(rc, os.strerror(rc))

    def release(self):
        self.unlock()


class Lock(_Lock):
    def locked(self):
        # Yes, this is horrible hack, and the same one used by Python
        # threadmodule.c. But this is part of Python lock interface.
        if self.acquire(blocking=False):
            self.release()
            return False
        return True


class RLock(Lock):
    def __init__(self):
        _Lock.__init__(self, recursive=True)


class Condition(object):
    """
    Condition class mimics Python native threading.Condition() API
    on top of the POSIX thread conditional variable synchronization
    primitive.
    """
    def __init__(self, lock=None):
        self.__lock = lock if lock else Lock()
        self.__cond = pthread.Cond(mutex=self.__lock)
        self.__signals = 0
        self.__waiters = 0
        # Export the lock's acquire() and release() methods
        self.acquire = self.__lock.acquire
        self.release = self.__lock.release

    def __enter__(self):
        return self.__lock.__enter__()

    def __exit__(self, *args):
        return self.__lock.__exit__(*args)

    def wait(self, timeout=None, balancing=True):
        # Balancing is an undocumented argument for Condition.wait()
        # It is relevent in python because it busy loops. Since the whole
        # purpose of this package is to not busy loop we just silently ignore
        # this argument.

        self.__waiters += 1
        try:
            if timeout is not None:
                self._wait_timeout(timeout)
            else:
                self._wait()
        finally:
            self.__waiters -= 1

    def notify(self):
        if self.__signals < self.__waiters:
            self.__signals += 1
        return self.__cond.signal()

    def notifyAll(self):
        self.__signals = self.__waiters
        return self.__cond.broadcast()

    notify_all = notifyAll

    def _wait(self):
        while True:
            self.__cond.wait()
            if self.__signals > 0:
                self.__signals -= 1
                break

    def _wait_timeout(self, timeout):
        bailout = time.time() + timeout
        abstime = pthread.timespec()
        abstime.tv_sec = int(bailout)
        abstime.tv_nsec = int((bailout - int(bailout)) * (10 ** 9))
        while True:
            if self.__cond.timedwait(abstime) == errno.ETIMEDOUT:
                break
            if self.__signals > 0:
                self.__signals -= 1
                break


_is_monkey_patched = False


def monkey_patch():
    """
    Hack threading and thread modules to use our classes

    Thus, Queue and SocketServer can easily enjoy them.
    """
    global _is_monkey_patched

    if _is_monkey_patched:
        return

    if 'thread' in sys.modules or 'threading' in sys.modules:
        # If thread was imported, some module may be using now the original
        # thread.allocate_lock. If threading was imported, it is already using
        # thread.allocate_lock for internal locks. Mixing different lock types
        # is a bad idea.
        raise RuntimeError("You must monkey_patch before importing thread or "
                           "threading modules")

    import thread
    thread.allocate_lock = Lock

    import threading
    threading.Condition = Condition
    threading.Lock = Lock
    threading.RLock = RLock

    _is_monkey_patched = True
