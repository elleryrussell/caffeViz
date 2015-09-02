from pyqtgraph.widgets.FileDialog import FileDialog

from caffeViz.Views import MainViewTemplate as MView
from caffeViz.Views import DisplayControlWidgetTemplate as DispCtrl
from caffeViz.flowcharts.flowcharts import NetFlowchart
from caffeViz.nodes.SolverNode import SolverNode

__author__ = 'err258'

import pyqtgraph as pg
from pyqtgraph import dockarea
from pyqtgraph import QtCore, QtGui
import sys
import numpy as np

from pyqtgraph.flowchart.library import getNodeTree
displayNodes = tuple(getNodeTree()['Display'].values())

class MainView(QtGui.QMainWindow):
    def __init__(self, modelFile=None, weightsFile=None, solverFile=None, filePath=None):
        if filePath is not None:
            modelFile = filePath + modelFile
            weightsFile = filePath + weightsFile
            solverFile = filePath + solverFile

        self.filePath = filePath

        self.plots = {}
        self.plotNodes = {}
        self.plotDocks = {}
        self.trainLossPlots = {}

        QtGui.QMainWindow.__init__(self)

        self.resize(1200, 800)
        self.setWindowTitle('caffeViz')
        self.tabWidget = QtGui.QTabWidget()
        self.tabWidget.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding))

        self.ui = MView.Ui_tabWidget()
        self.ui.setupUi(self.tabWidget)

        cw = QtGui.QWidget()
        cw.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding))
        layout = QtGui.QGridLayout()
        cw.setLayout(layout)
        layout.addWidget(self.tabWidget)
        self.setCentralWidget(cw)

        self.fc = NetFlowchart(prototxt=modelFile, weights=weightsFile)
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
        self.tabWidget.setCurrentIndex(1)
        self.tabWidget.setCurrentIndex(2)
        self.fc.sigDisplayNodeAdded.connect(self.addPlot)

        self.displayControlDock = pg.dockarea.Dock('Control')
        formWidget = pg.QtGui.QWidget()
        displayCtrlUi = DispCtrl.Ui_displayControlWidget()
        displayCtrlUi.setupUi(formWidget)
        displayCtrlUi.previousBtn.clicked.connect(self.updateDisplay)
        displayCtrlUi.updateBtn.clicked.connect(self.updateDisplay)
        displayCtrlUi.nextBtn.clicked.connect(self.updateDisplay)
        self.displayCtrlUi = displayCtrlUi

        self.displayControlDock.addWidget(formWidget)
        self.ui.displayArea.addDock(self.displayControlDock, position='top')

        self.solverNode = SolverNode('solver', solverFile, weightsFile, filePath)
        self.solverNode.sigOutputDataChanged.connect(self.updateTrainPlots)
        self.ui.trainButton.pressed.connect(self.solverNode.trainNet)
        self.ui.stopButton.pressed.connect(self.solverNode.stopTraining)
        self.ui.resumeButton.pressed.connect(self.solverNode.resumeTraining)
        self.ui.loadSolverButton.pressed.connect(self.loadSolver)
        self.ui.saveSolverButton.pressed.connect(self.saveSolver)
        self.ui.trainParamTree.addParameters(self.solverNode.param)
        zeros = np.zeros(1)
        self.trainPlotItem = self.ui.trainGraphicsLayout.plotItem

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
        if isinstance(plotNode, displayNodes):
            plotNode.setPlot(plot)

        plotDock = pg.dockarea.Dock(name)
        self.plotDocks[name] = plotDock
        plotDock.addWidget(plot)
        self.ui.displayArea.addDock(plotDock)
        self.tabWidget.update()

        # for name, plotNode in self.plotNodes.items():
        #     plotNode.setPlotList(self.plots)

    def updateDisplay(self):
        sender = self.sender()
        if sender.objectName() == u'previousBtn':
            self.selectInput(-1)
        elif sender.objectName() == u'nextBtn':
            self.fc.process(forward=True)
        else:
            self.fc.process(forward=False)

    def loadSolver(self, fileName=None, startDir=None):
        if fileName is None:
            if startDir is None:
                startDir = self.filePath
            if startDir is None:
                startDir = '.'
            self.fileDialog = FileDialog(None, "Load Flowchart..", startDir, "Protobuf (*.prototxt)")
            # self.fileDialog.setFileMode(QtGui.QFileDialog.AnyFile)
            # self.fileDialog.setAcceptMode(QtGui.QFileDialog.AcceptSave)
            self.fileDialog.show()
            self.fileDialog.fileSelected.connect(self.loadSolver)
            return
        fileName = unicode(fileName)
        self.solverNode.setProto(fileName)

    def saveSolver(self, fileName=None, startDir=None, suggestedFileName='solver.prototxt'):
        if fileName is None:
            if startDir is None:
                startDir = self.filePath
            if startDir is None:
                startDir = '.'
            self.fileDialog = FileDialog(None, "Save Solver..", startDir, "Prototxt (*.prototxt)")
            self.fileDialog.setAcceptMode(QtGui.QFileDialog.AcceptSave)
            self.fileDialog.show()
            self.fileDialog.fileSelected.connect(self.saveSolver)
            return

        fileName = unicode(fileName)
        self.solverNode.writeProto(fileName)

    def updateTrainPlots(self, data):
        for lossName, color in dict(trainLoss='b', testLoss='g', testAcc='r').items():
            for trainLossName, trainLossArr in data[lossName].items():
                try:
                    self.trainLossPlots[trainLossName].setData(trainLossArr)
                except KeyError:
                    self.trainLossPlots[trainLossName] = self.trainPlotItem.plot(trainLossArr, pen=color,
                                                                                 name=trainLossName)

    def stopTraining(self):
        pass

    def resumeTraining(self):
        pass


if __name__ == '__main__':
    pg.mkQApp()  # layout.addWidget(w)
    # layout.addWidget(w.chartWidget, 0, 1)
    # # w.chartWidget.moveDock()
    # win.show()

    import os.path

    # net = caffe.Net('aprototxt.prototxt', caffe.TEST)

    base_path = os.path.expanduser('~')
    # model_dir = base_path + '/caffe/models/'
    model_dir = base_path + '/caffeProjects/pascalContext/'

    # net_dir = 'bvlc_reference_caffenet/'
    # net_dir = 'pascalContextFCN8/'
    net_dir = 'googleNet/'

    filePath = model_dir + net_dir

    modelName = 'train_val.prototxt'
    weightsName = 'bvlc_googlenet_iter_1400.caffemodel'
    # weightsName = 'fcn-8s-pascalcontext.caffemodel'
    # weightsName = 'bvlc_reference_caffenet.caffemodel'
    solverName = 'solver.prototxt'

    win = MainView(modelFile=modelName, weightsFile=weightsName, solverFile=solverName, filePath=filePath)
    win.show()
    # win.ui.trainButton.click()

    # imageNode0 = win.fc.createNode('ImagePlot', pos=(4*120, 16*120))
    # cropNode = win.fc.nodes()['crop.2']
    # win.fc.connectTerminals(cropNode['score.o'], imageNode0['image'])
    #
    # imageNode1 = win.fc.createNode('ImagePlot', pos=(0*120, 0*120))
    # dataNode = win.fc.nodes()['data']
    # win.fc.connectTerminals(dataNode['data.o'], imageNode1['image'])
    #
    # imageNode2 = win.fc.createNode('ImagePlot', pos=(2*120, 0*120))
    # labelNode = win.fc.nodes()['label']
    # win.fc.connectTerminals(labelNode['label.o'], imageNode2['image'])


    # win.displayCtrlUi.updateBtn.click()


    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()