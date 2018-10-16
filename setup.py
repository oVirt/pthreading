from distutils.core import setup

import pthreading


setup(name='pthreading',
      version=pthreading.__version__,
      license='GPLv2+',
      url='https://gerrit.ovirt.org/gitweb?p=pthreading.git',
      maintainer='Marcin Sobczyk',
      maintainer_email='msobczyk@redhat.com',
      py_modules=['pthreading', 'pthread'],
      platforms=['Linux'],
      description=pthreading.__doc__.split('\n')[0],
      long_description=pthreading.__doc__,
      )
