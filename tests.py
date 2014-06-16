#
# Copyright 2012 Red Hat, Inc.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#
import functools
import threading
import unittest
import logging
from time import sleep, time
import sys
from contextlib import contextmanager

import pthreading


class TestCaseBase(unittest.TestCase):
    log = logging.getLogger('test')


def without_module(name):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*a, **kw):
            module = sys.modules.pop(name)
            try:
                return f(*a, **kw)
            finally:
                sys.modules[name] = module
        return wrapper
    return decorator


class WithoutModuleTests(TestCaseBase):

    def setUp(self):
        self.assertIn('sys', sys.modules)

    def tearDown(self):
        self.assertIn('sys', sys.modules)

    @without_module('sys')
    def testWithout(self):
        self.assertNotIn('sys', sys.modules)


class MonkeyPatchTests(TestCaseBase):

    def tearDown(self):
        pthreading._is_monkey_patched = False

    @without_module('thread')
    @without_module('threading')
    def testMonkeyPatch(self):
        pthreading.monkey_patch()
        self.checkMonkeyPatch()

    @without_module('thread')
    @without_module('threading')
    def testMonkeyPatchTwice(self):
        pthreading.monkey_patch()
        pthreading.monkey_patch()
        self.checkMonkeyPatch()

    @without_module('thread')
    def testMonkeyPatchRaisesThread(self):
        assert 'threading' in sys.modules
        self.assertRaises(RuntimeError, pthreading.monkey_patch)

    @without_module('threading')
    def testMonkeyPatchRaisesThreading(self):
        assert 'thread' in sys.modules
        self.assertRaises(RuntimeError, pthreading.monkey_patch)

    def checkMonkeyPatch(self):
        import thread
        import threading
        self.assertEquals(thread.allocate_lock, pthreading.Lock)
        self.assertEquals(threading.Lock, pthreading.Lock)
        self.assertEquals(threading.RLock, pthreading.RLock)
        self.assertEquals(threading.Condition, pthreading.Condition)


class LockTests(TestCaseBase):
    def _testAcquire(self, lock):
        self.assertTrue(lock.acquire())

    def _testRelease(self, lock):
        lock.acquire()
        lock.release()
        self.assertTrue(lock.acquire(False))

    def testAcquireLock(self):
        self._testAcquire(pthreading.Lock())

    def testAcquireRLock(self):
        self._testAcquire(pthreading.RLock())

    def testReleaseLock(self):
        self._testRelease(pthreading.Lock())

    def testReleaseRLock(self):
        self._testRelease(pthreading.RLock())

    def testAcquireNonblocking(self):
        lock = pthreading.Lock()
        lock.acquire()
        self.assertFalse(lock.acquire(False))

    def testAcquireRecursive(self):
        lock = pthreading.RLock()
        self.assertTrue(lock.acquire())
        self.assertTrue(lock.acquire(False))

    def testLocked(self):
        lock = pthreading.Lock()
        self.assertFalse(lock.locked())
        with lock:
            self.assertTrue(lock.locked())
        self.assertFalse(lock.locked())


class ConditionTest(TestCaseBase):

    CONCURRENCY = 10
    log = logging.getLogger("ConditionTest")

    def setUp(self):
        self.waiting = 0
        self.wokeup = 0
        self.cond = None

    @contextmanager
    def running(self, func):
        """
        Starts CONCURRENCY threads running func. Yields when all threads are
        waiting.
        """
        waiters = []
        try:
            self.log.info("Starting waiter threads")
            for n in range(self.CONCURRENCY):
                t = threading.Thread(target=func)
                t.daemon = True
                t.start()
                waiters.append(t)

            self.log.info("Waiting for waiter threads")
            while True:
                sleep(0.05)
                with self.cond:
                    if self.waiting == self.CONCURRENCY:
                        break
            self.log.info("Waiter threads ready")
            with self.cond:
                self.assertEquals(self.wokeup, 0)

            yield
        finally:
            self.log.info("Joining waiter threads")
            for t in waiters:
                t.join()


class ConditionNotifyTests(ConditionTest):
    """
    Test that Condition.wait() returns after notify().
    """

    def check(self, lock):
        self.cond = pthreading.Condition(lock)

        for i in range(self.CONCURRENCY):
            with self.cond:
                self.cond.notify()

        def waiter():
            with self.cond:
                self.waiting += 1
                self.cond.wait()
                self.wokeup += 1

        with self.running(waiter):
            self.log.info("Notifying waiter threads")
            for i in range(self.CONCURRENCY):
                with self.cond:
                    self.cond.notify()

        self.assertEquals(self.wokeup, self.CONCURRENCY)

    def testDefaultLock(self):
        self.check(lock=None)

    def testLock(self):
        self.check(lock=pthreading.Lock())

    def testRLock(self):
        self.check(lock=pthreading.RLock())


class ConditionNotifyAllTests(ConditionTest):
    """
    Test that Condition.wait() returns after notifyAll().
    """

    def check(self, lock):
        self.cond = pthreading.Condition(lock)

        with self.cond:
            self.cond.notifyAll()

        def waiter():
            with self.cond:
                self.waiting += 1
                self.cond.wait()
                self.wokeup += 1

        with self.running(waiter):
            self.log.info("Notifying waiter threads")
            with self.cond:
                self.cond.notifyAll()

        self.assertEquals(self.wokeup, self.CONCURRENCY)

    def testDefaultLock(self):
        self.check(lock=None)

    def testLock(self):
        self.check(lock=pthreading.Lock())

    def testRLock(self):
        self.check(lock=pthreading.RLock())


class ConditionTimeoutTests(ConditionTest):
    """
    Test that Condition.wait(timeout) returns after deadline.
    """

    def check(self, lock, timeout):
        self.cond = pthreading.Condition(lock)
        self.wokeup_before_deadline = 0
        self.wokeup_after_deadline = 0

        def waiter():
            with self.cond:
                deadline = time() + timeout
                self.waiting += 1
                self.cond.wait(timeout)
                if time() < deadline:
                    self.wokeup_before_deadline += 1
                else:
                    self.wokeup_after_deadline += 1

        with self.running(waiter):
            pass

        self.assertEquals(self.wokeup_before_deadline, 0)
        self.assertEquals(self.wokeup_after_deadline, self.CONCURRENCY)

    def testIntegerDefaultLock(self):
        self.check(lock=None, timeout=1)

    def testIntegerLock(self):
        self.check(lock=pthreading.Lock(), timeout=1)

    def testIntegerRLock(self):
        self.check(lock=pthreading.RLock(), timeout=1)

    def testFloatDefaultLock(self):
        self.check(lock=None, timeout=0.1)

    def testFloatLock(self):
        self.check(lock=pthreading.Lock(), timeout=0.1)

    def testFloatRLock(self):
        self.check(lock=pthreading.RLock(), timeout=0.1)


class ConditionTimeoutNotifyTests(ConditionTest):
    """
    Test that Condition.wait(timeout) return before deadline on notify().
    """

    TIMEOUT = 1

    def check(self, lock):
        self.cond = pthreading.Condition(lock)
        self.wokeup_before_deadline = 0
        self.wokeup_after_deadline = 0

        def waiter():
            with self.cond:
                deadline = time() + self.TIMEOUT
                self.waiting += 1
                self.cond.wait(self.TIMEOUT)
                if time() < deadline:
                    self.wokeup_before_deadline += 1
                else:
                    self.wokeup_after_deadline += 1

        with self.running(waiter):
            self.log.info("Notifying waiter threads")
            with self.cond:
                self.cond.notifyAll()

        self.assertEquals(self.wokeup_before_deadline, self.CONCURRENCY)
        self.assertEquals(self.wokeup_after_deadline, 0)

    def testDefaultLock(self):
        self.check(lock=None)

    def testLock(self):
        self.check(lock=pthreading.Lock())

    def testRLock(self):
        self.check(lock=pthreading.RLock())


class EventTests(TestCaseBase):
    def _test(self, timeout):
        self.log.info("Creating Event object")
        e = threading.Event()

        def setter():
            self.log.info("Setter thread is sleeping")
            sleep(2)
            self.log.info("Setter thread is setting")
            e.set()
            self.log.info("Event object is set (%s) :D", e.is_set())

        self.log.info("Starting setter thread")
        threading.Thread(target=setter).start()
        self.log.info("Waiting for salvation")
        res = e.wait(timeout)
        self.assertTrue(res is not False)

    def testPassWithTimeout(self):
        self._test(5)

    def testPassWithoutTimeout(self):
        self._test(None)

    def testNotPassTimeout(self):
        self.log.info("Creating Event object")
        e = threading.Event()
        self.log.info("Waiting for salvation (That will never come)")
        res = e.wait(0.5)
        self.assertFalse(res)

    def testZeroTimeout(self):
        self.log.info("Creating Event object")
        e = threading.Event()
        self.log.info("Waiting 0 for salvation (That will never come)")
        res = e.wait(0)
        self.assertFalse(res)

if __name__ == '__main__':
    unittest.main()
