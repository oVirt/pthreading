Reimplement threading.Lock, RLock and Condition with libpthread

The pthreading module provides Lock and Condition synchronization objects compatible with Python native threading module. The implementation, however, is based on POSIX thread library as delivered by the libpthread. Lock and Condition are designed to be a drop-in replacement for their respective threading counterpart.

Take a look at threading.py of Python 2. Notice that Event.wait() wakes 20 times a second and checks if the event has been set. This CPU hogging has been fixed in Python 3, but is not expected to change during Python 2 lifetime.

To avoid this waste of resources, put in your main module:

```python
import pthreading
pthreading monkey_patch()
```

This would hack the Linux-native threading module, and make it use Linux-native POSIX synchronization objects.

The pthreading code was originally written as part of Vdsm by Cyril Plisko, Saggi Mizrahi and others. For questions, comments and patches please contact vdsm-devel.
