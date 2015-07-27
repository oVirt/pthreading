from distutils.core import setup

import pthreading


setup(name='pthreading',
      version=pthreading.__version__,
      license='GPLv2+',
      url='http://git.fedorahosted.org/git/?p=pthreading.git',
      maintainer='Dan Kenigsberg',
      maintainer_email='danken@redhat.com',
      py_modules=['pthreading', 'pthread'],
      platforms=['Linux'],
      description=pthreading.__doc__.split('\n')[0],
      long_description=pthreading.__doc__,
      )
