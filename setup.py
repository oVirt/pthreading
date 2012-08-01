from distutils.core import setup
from distutils.cmd import Command
from unittest import TextTestRunner, TestLoader

import pthreading


class TestCommand(Command):
    user_options = []
    description = "run unit tests"

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import tests

        loader = TestLoader()
        t = TextTestRunner()
        t.run(loader.loadTestsFromModule(tests))

setup(name='pthreading',
      version='0.1.1',
      license='GPLv2+',
      url='http://git.fedorahosted.org/git/?p=pthreading.git',
      maintainer='Dan Kenigsberg',
      maintainer_email='danken@redhat.com',
      py_modules=['pthreading', 'pthread'],
      platforms=['Linux'],
      description=pthreading.__doc__.split('\n')[0],
      long_description=pthreading.__doc__,
      cmdclass={'test': TestCommand},
      )
