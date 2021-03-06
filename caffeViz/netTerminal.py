__author__ = 'err258'
from pyqtgraph.flowchart.Terminal import Terminal, ConnectionItem
from pyqtgraph import QtGui
from pyqtgraph.Point import Point


class NetConnectionItem(ConnectionItem):
    """Override connection item to use cubic spline paths"""
    def generatePath(self, start, stop, vertical=True):
        path = QtGui.QPainterPath()
        path.moveTo(start)
        if self.style['shape'] == 'cubic':
            path.cubicTo(Point(start.x(), stop.y()), Point(stop.x(), start.y()), Point(stop.x(), stop.y()))
        else:
            path = ConnectionItem.generatePath(self, start, stop)
        return path


class NetTerminal(Terminal):
    """Subclass Terminal to override naming behavior for inputs and outputs"""

    def name(self):
        return self._name[:-len('.o')]

    def rename(self, name):
        oldName = self._name
        if self.isInput():
            ext = '.i'
        else:
            ext = '.o'
        self._name = name + ext
        self.node().terminalRenamed(self, oldName)
        self.graphicsItem().termRenamed(name)

    def connectTo(self, term, connectionItem=None, rename=True):
        Terminal.connectTo(self, term, connectionItem=connectionItem)
        if rename and isinstance(term, NetTerminal):
            # caffe expects input and output terminals to match names
            if self.isInput():
                self.rename(term.name())
            else:
                term.rename(self.name())
