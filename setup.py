from distutils.core import setup

setup(
    name='caffeViz',
    version='1.0',
    packages=['nodes'],
    url='',
    license='well...',
    author='ellery',
    author_email='ellery.rrussell@gmail.com',
    description='tools for caffe',
    requires=['caffe', 'pyqtgraph', 'toposort']
)
