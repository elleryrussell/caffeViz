from Views.MainViewTemplate import Ui_tabWidget
from flowcharts.flowcharts import NetFlowchart

__author__ = 'err258'

import pyqtgraph as pg
from pyqtgraph import dockarea
from pyqtgraph import QtCore, QtGui
import sys
from pyqtgraph.flowchart.library import Display


class MainView(QtGui.QMainWindow):
    def __init__(self, model_file=None, weights_file=None):

        self.plots = {}
        self.plotNodes = {}
        self.plotDocks = {}

        QtGui.QMainWindow.__init__(self)

        self.resize(1200, 800)
        self.setWindowTitle('caffeViz')
        self.tabWidget = QtGui.QTabWidget()
        self.tabWidget.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding))

        self.ui = Ui_tabWidget()
        self.ui.setupUi(self.tabWidget)

        cw = QtGui.QWidget()
        cw.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding))
        layout = QtGui.QGridLayout()
        cw.setLayout(layout)
        layout.addWidget(self.tabWidget)
        self.setCentralWidget(cw)

        self.fc = NetFlowchart(prototxt=model_file, weights=weights_file)
        self.fc.sigChartChanged.connect(self.fc.configNode)
        w = self.fc.widget()

        # QtGui.QGridLayout(self.ui.flowchartCtrlWidget)
        # QtGui.QGridLayout(self.ui.flowchartCtrlWidget_2)
        # QtGui.QGridLayout(self.ui.flowchartWidget)
        # QtGui.QGridLayout(self.ui.flowchartWidget_2)
        self.ui.splitter.addWidget(self.ui.displayLayout)
        # QtGui.QGridLayout(self.ui.plotWidget)

        # self.plotLabel = QtGui.QLabel()
        # self.plotLabelDock = dockarea.Dock('label')
        # self.plotLabelDock.addWidget(self.plotLabel)
        # self.ui.plotWidget.addDock(self.plotLabelDock)
        # self.hoverDock.addWidget(self.hoverText)
        # self.addDock(self.hoverDock, 'bottom')
        # self.ui.plotWidget.addDock

        ctrlList = w.ui.ctrlList
        ctrlList.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        w.ui.ctrlList = ctrlList
        # w = w._nodes['LayerNode.0'].ctrlWidget()
        w.sizePolicy().setHorizontalPolicy(QtGui.QSizePolicy.MinimumExpanding)

        self.tabWidget.currentChanged.connect(self.tabChanged)
        self.tabWidget.setCurrentIndex(0)
        self.fc.sigDisplayNodeAdded.connect(self.addPlot)

    def tabChanged(self, tabIndex):
        if tabIndex == 0:
            self.setTab0()
        elif tabIndex == 2:
            self.setTab2()
        # self.tabWidget.update()

    def setTab0(self):
        self.ui.flowchartCtrlWidget.layout().addWidget(self.fc.widget())
        self.ui.flowchartWidget.layout().addWidget(self.fc.widget().chartWidget)
        self.tabWidget.update()

    def setTab2(self):
        self.ui.flowchartCtrlWidget_2.layout().addWidget(self.fc.widget())
        self.ui.flowchartWidget_2.layout().addWidget(self.fc.widget().chartWidget)
        # self.ui.plotWidget.layout().addWidget(self.plotLabel)
        self.tabWidget.update()

    def addPlot(self, plotNode):
        name = plotNode.name()
        plot = pg.PlotWidget(name=name)
        self.plots[name] = plot
        self.plotNodes[name] = plotNode
        # get class of plot node to determine type of plot
        if isinstance(plotNode, Display.PlotWidgetNode):
            plotNode.setPlot(plot)

        plotDock = pg.dockarea.Dock(name)
        self.plotDocks[name] = plotDock
        plotDock.addWidget(plot)
        self.ui.displayArea.addDock(plotDock)
        self.tabWidget.update()

        for name, plotNode in self.plotNodes.items():
            plotNode.setPlotList(self.plots)


if __name__ == '__main__':
    pg.mkQApp()  # layout.addWidget(w)
    # layout.addWidget(w.chartWidget, 0, 1)
    # # w.chartWidget.moveDock()
    # win.show()

    model_dir = '/Users/err258/caffe/models/'
    # net_dir = 'bvlc_reference_caffenet/'
    net_dir = '91eece041c19ff8968ee/'
    dir = model_dir + net_dir
    # model_path = '/train_val.prototxt'
    model_path = 'train_val.prototxt'

    weights_path = 'fcn-8s-pascalcontext.caffemodel'
    # rel_path = 'bvlc_reference_caffenet/deploy.prototxt'
    model_file = dir + model_path

    weights_file = dir + weights_path

    win = MainView(model_file, weights_file=weights_file)
    win.show()

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()