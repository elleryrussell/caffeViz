from distutils.core import setup

setup(
    name='caffeViz',
    version='1.0',
    packages=['caffeViz', 'caffeViz.views', 'caffeViz.nodes', 'caffeViz.flowcharts'],
    url='',
    license='MIT',
    author='ellery',
    author_email='ellery.rrussell@gmail.com',
    description='tools for caffe',
    requires=['caffe', 'pyqtgraph', 'toposort']
)
