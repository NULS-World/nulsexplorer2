from setuptools import setup, find_packages
import sys, os

version = '2.0'

setup(name='nulsexplorer',
      version=version,
      description="Nuls Chain Explorer",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='python3 blockchain nuls explorer',
      author='Moshe Malawach',
      author_email='moshe.malawach@protonmail.com',
      url='',
      license='MIT',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
          "pymongo",
          "motor",
          "aiohttp>=3.3.2",
          "aiohttp-session[secure]",
          "aiohttp-jinja2",
          "aiohttp_cors",
          "aiocache",
          "aiocron",
          "pyyaml",
          "configmanager",
          "uvloop",
          "jsonrpc-async"
      ],
      entry_points={
          'console_scripts':
              ['nulsexplorer = nulsexplorer.commands:launch_explorer']
      },
      )
