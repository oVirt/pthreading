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
import logging
from time import sleep, time
import sys
from contextlib import contextmanager
import pytest
import pthreading

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


class TestWithoutModule:

    def setup_method(self, m):
        assert 'sys' in sys.modules

    def teardown_method(self, m):
        assert 'sys' in sys.modules

    @without_module('sys')
    def test_without_module(self):
        assert 'sys' not in sys.modules


class TestMonkeyPatch:

    def teardown_method(self, m):
        pthreading._is_monkey_patched = False

    @without_module('thread')
    @without_module('threading')
    def test_monkey_patch(self):
        pthreading.monkey_patch()
        self.check_monkey_patch()

    @without_module('thread')
    @without_module('threading')
    def test_monkey_patch_twice(self):
        pthreading.monkey_patch()
        pthreading.monkey_patch()
        self.check_monkey_patch()

    @without_module('thread')
    def test_monkey_patch_raises_thread(self):
        assert 'threading' in sys.modules
        pytest.raises(RuntimeError, pthreading.monkey_patch)

    @without_module('threading')
    def test_monkey_patch_raises_threading(self):
        assert 'thread' in sys.modules
        pytest.raises(RuntimeError, pthreading.monkey_patch)

    def check_monkey_patch(self):
        import thread
        import threading
        assert thread.allocate_lock is pthreading.Lock
        assert threading.Lock is pthreading.Lock
        assert threading.RLock is pthreading.RLock
        assert threading.Condition is pthreading.Condition


class TestLock:

    def _test_acquire(self, lock):
        assert lock.acquire()

    def _test_release(self, lock):
        lock.acquire()
        lock.release()
        assert lock.acquire(False)

    def test_acquire_lock(self):
        self._test_acquire(pthreading.Lock())

    def test_acquire_rlock(self):
        self._test_acquire(pthreading.RLock())

    def test_release_lock(self):
        self._test_release(pthreading.Lock())

    def test_release_rlock(self):
        self._test_release(pthreading.RLock())

    def test_acquire_nonblocking(self):
        lock = pthreading.Lock()
        lock.acquire()
        assert not lock.acquire(False)

    def test_acquire_recursive(self):
        lock = pthreading.RLock()
        assert lock.acquire()
        assert lock.acquire(False)

    def test_locked(self):
        lock = pthreading.Lock()
        assert not lock.locked()
        with lock:
            assert lock.locked()
        assert not lock.locked()


class TestCondition:

    CONCURRENCY = 10

    def setup_method(self, m):
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
            log.info("Starting waiter threads")
            for n in range(self.CONCURRENCY):
                t = threading.Thread(target=func)
                t.daemon = True
                t.start()
                waiters.append(t)

            log.info("Waiting for waiter threads")
            while True:
                sleep(0.05)
                with self.cond:
                    if self.waiting == self.CONCURRENCY:
                        break
            log.info("Waiter threads ready")
            with self.cond:
                assert self.wokeup == 0

            yield
        finally:
            log.info("Joining waiter threads")
            for t in waiters:
                t.join()


class TestConditionNotify(TestCondition):
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
            log.info("Notifying waiter threads")
            for i in range(self.CONCURRENCY):
                with self.cond:
                    self.cond.notify()

        assert self.wokeup == self.CONCURRENCY

    def test_default_lock(self):
        self.check(lock=None)

    def test_lock(self):
        self.check(lock=pthreading.Lock())

    def test_rlock(self):
        self.check(lock=pthreading.RLock())


class TestConditionNotifyAll(TestCondition):
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
            log.info("Notifying waiter threads")
            with self.cond:
                self.cond.notifyAll()

        assert self.wokeup == self.CONCURRENCY

    def test_default_lock(self):
        self.check(lock=None)

    def test_lock(self):
        self.check(lock=pthreading.Lock())

    def test_rlock(self):
        self.check(lock=pthreading.RLock())


class TestConditionTimeout(TestCondition):
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

        assert self.wokeup_before_deadline == 0
        assert self.wokeup_after_deadline == self.CONCURRENCY

    def test_integer_default_lock(self):
        self.check(lock=None, timeout=1)

    def test_integer_lock(self):
        self.check(lock=pthreading.Lock(), timeout=1)

    def test_integer_rlock(self):
        self.check(lock=pthreading.RLock(), timeout=1)

    def test_float_default_lock(self):
        self.check(lock=None, timeout=0.1)

    def test_float_lock(self):
        self.check(lock=pthreading.Lock(), timeout=0.1)

    def test_float_rlock(self):
        self.check(lock=pthreading.RLock(), timeout=0.1)


class TestConditionTimeoutNotify(TestCondition):
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
            log.info("Notifying waiter threads")
            with self.cond:
                self.cond.notifyAll()

        assert self.wokeup_before_deadline == self.CONCURRENCY
        assert self.wokeup_after_deadline == 0

    def test_default_lock(self):
        self.check(lock=None)

    def test_lock(self):
        self.check(lock=pthreading.Lock())

    def test_rlock(self):
        self.check(lock=pthreading.RLock())


class TestEvent:

    def _test(self, timeout):
        log.info("Creating Event object")
        e = threading.Event()

        def setter():
            log.info("Setter thread is sleeping")
            sleep(2)
            log.info("Setter thread is setting")
            e.set()
            log.info("Event object is set (%s) :D", e.is_set())

        log.info("Starting setter thread")
        threading.Thread(target=setter).start()
        log.info("Waiting for salvation")
        res = e.wait(timeout)
        assert res

    def test_pass_with_timeout(self):
        self._test(5)

    def test_pass_without_timeout(self):
        self._test(None)

    def test_not_pass_timeout(self):
        log.info("Creating Event object")
        e = threading.Event()
        log.info("Waiting for salvation (That will never come)")
        res = e.wait(0.5)
        assert not res

    def test_zero_timeout(self):
        log.info("Creating Event object")
        e = threading.Event()
        log.info("Waiting 0 for salvation (That will never come)")
        res = e.wait(0)
        assert not res
