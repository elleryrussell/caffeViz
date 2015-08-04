__author__ = 'err258'
from pyqtgraph.flowchart.Terminal import Terminal, ConnectionItem
from pyqtgraph import QtGui
from pyqtgraph.Point import Point


class NetConnectionItem(ConnectionItem):
    def generatePath(self, start, stop, vertical=True):
        path = QtGui.QPainterPath()
        path.moveTo(start)
        if self.style['shape'] == 'cubic':
            path.cubicTo(Point(start.x(), stop.y()), Point(stop.x(), start.y()), Point(stop.x(), stop.y()))
        else:
            path = ConnectionItem.generatePath(self, start, stop)
        return path

class NetTerminal(Terminal):
    def name(self):
        # print self._name[:-len('.o')]
        return self._name[:-len('.o')]

    def rename(self, name):
        oldName = self._name
        self._name = name + oldName[-len('.o'):]
        self.node().terminalRenamed(self, oldName)
        self.graphicsItem().termRenamed(name)
