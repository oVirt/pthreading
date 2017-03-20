%define name pthreading
%define version 0.1.5
%define unmangled_version 0.1.5
%define release 1

Summary: Reimplement threading.Lock, RLock and Condition with libpthread
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{unmangled_version}.tar.gz
License: GPLv2+
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Dan Kenigsberg <danken@redhat.com>
Url: https://github.com/oVirt/pthreading

%description
Reimplement threading.Lock, RLock and Condition with libpthread

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
others. For questions, comments and patches please contact `ovirt-devel
<mailto:devel@ovirt>`_.


%prep
%setup -n %{name}-%{unmangled_version}

%build
python setup.py build

%install
python setup.py install -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
