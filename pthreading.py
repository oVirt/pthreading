#
# Copyright 2011-2012 Red Hat, Inc.
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

Take a look at threading.py of Python 2. Notice that Event.wait() wakes 20
times a second and checks if the event has been set. This CPU hogging has been
fixed in Python 3, but is not expected to change during Python 2 lifetime.

To avoid this waste of resources, put in your main module::

    import pthreading
    pthreading monkey_patch()

This would hack the Linux-native threading module, and make it use Linux-native
POSIX synchronization objects.

The pthreading code was originally written as part of
`Vdsm <http://wiki.ovirt.org/wiki/Vdsm>`_ by Cyril Plisko, Saggi Mizrahi and
others. For questions, comments and patches please contact `vdsm-devel
<mailto:vdsm-devel@lists.fedorahosted.org>`_.
"""

import time
import errno
import os

import pthread


class Lock(pthread.Mutex):
    """
    Lock class mimics Python native threading.Lock() API on top of
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


class RLock(Lock):
    def __init__(self):
        pthread.Mutex.__init__(self, recursive=True)


class Condition(object):
    """
    Condition class mimics Python native threading.Condition() API
    on top of the POSIX thread conditional variable synchronization
    primitive.
    """
    def __init__(self, lock=None):
        self.__lock = lock if lock else Lock()
        self.__cond = pthread.Cond(mutex=self.__lock)
        # Export the lock's acquire() and release() methods
        self.acquire = self.__lock.acquire
        self.release = self.__lock.release

    def __enter__(self):
        return self.__lock.__enter__()

    def __exit__(self, *args):
        return self.__lock.__exit__(*args)

    def wait(self, timeout=None):
        if timeout is not None:
            bailout = time.time() + timeout
            abstime = pthread.timespec()
            abstime.tv_sec = int(bailout)
            abstime.tv_nsec = int((bailout - int(bailout)) * (10 ** 9))
            return self.__cond.timedwait(abstime)
        else:
            return self.__cond.wait()

    def notify(self):
        return self.__cond.signal()

    def notifyAll(self):
        return self.__cond.broadcast()

    notify_all = notifyAll


def monkey_patch():
    """
    Hack threading module to use our classes

    Thus, Queue and SocketServer can easily enjoy them.
    """

    import threading

    threading.Condition = Condition
    threading.Lock = Lock
    threading.RLock = RLock
