from pyqtgraph.flowchart.Flowchart import Flowchart, FlowchartWidget
from pyqtgraph.flowchart.Terminal import Terminal
from caffe.proto.caffe_pb2 import NetParameter as NetProto
import toposort
from pyqtgraph.flowchart.library import getNodeTree

from caffeViz.netTerminal import NetConnectionItem
from caffeViz.protobufUtils import parsePrototxt

displayNodes = tuple(getNodeTree()['Display'].values())

from pyqtgraph.widgets.FileDialog import FileDialog

from caffeViz.nodes.LayerNodes import LayerNode

__author__ = 'ellery'

from pyqtgraph.Qt import QtGui, QtCore
import caffe


class NetFlowchart(Flowchart):
    sigDisplayNodeAdded = QtCore.Signal(object) # node

    def __init__(self, prototxt=None, weights=None):
        self.nodeList = []
        self.displayNodes = {}
        self.holdUpdateConnects = True
        self.netNeedsUpdate = True
        self.netNeedsEval = True
        self.nextData = None
        Flowchart.__init__(self, terminals={
            'dataIn': {'io': 'in'},
            'dataOut': {'io': 'out'}
        })

        # self.widget().__class__ = LFlowchartCtrlWidget
        # self.widget().__init__(self)

        if prototxt is None:
            self.proto = NetProto()
            self.layerList = self.proto.layer
            self.plotList = {}
        else:
            self.proto = parsePrototxt(prototxt, 'net')
            self.layerList = self.proto.layer
            # for old proto
            if len(self.layerList)==0:
                self.layerList = self.proto.layers

        self.weights = weights

        for proto in self.layerList:
            print proto
        # self.setLibrary(LayerNodes.library)
        self.initNodes()

        self.configNodes()

        self.holdUpdateConnects = False
        self.connectNodes()

        fcw = self.widget().chartWidget
        fcw.viewDock.sizePolicy().setHorizontalPolicy(QtGui.QSizePolicy.Maximum)

        fcw.moveDock(fcw.hoverDock, 'bottom', fcw.viewDock)
        fcw.moveDock(fcw.selDock, 'right', fcw.hoverDock)

        # ctrlWidget = self.widget()
        # ctrlWidget.chartWidget = LFlowchartWidget(ctrlWidget.chart, ctrlWidget)
        # self.setNodes()
        # self.connectNodes()

    def addNode(self, node, name, pos=None):
        Flowchart.addNode(self, node, name, pos=pos)
        node.sigTerminalAdded.connect(self.connectNodes)
        node.sigTerminalRemoved.connect(self.connectNodes)
        node.sigTerminalRenamed.connect(self.connectNodes)

    def initNodes(self):
        ## eventually this should be a list of tops from parsePrototxt
        if self.layerList:
            ypos, xpos = 0, -120
            lastNum = 1
            for i, layerParam in enumerate(self.layerList):
                name = layerParam.name

                digits = [int(s) for s in name if s.isdigit()]
                if len(digits)==0:
                    primaryDigit=0
                else:
                    primaryDigit = digits[0]
                # numeric suffix of layer
                if lastNum != primaryDigit:
                    ypos += 120
                    xpos = 0
                    # xpos += node.graphicsItem().bounds.width() + 20
                else:
                    xpos += 120
                lastNum = primaryDigit
                node = self.createNode("Layer", name=name, pos=(xpos, ypos))
                # node.configFromLayerSpec(layerParam)
                # node.configFromLayerSpec(layerParam)
                # node.sigRenamed.connect(self.nodeRenamed)
                self.nodeList.append(node)
            ypos += 150
            self.outputNode.graphicsItem().setPos(xpos, 0)
        else:
            # default node config
            node = self.createNode("Layer")

    def createNode(self, nodeType, name=None, pos=None):
        if name in self._nodes:
            name2 = name
            n = 1
            while name2 in self._nodes:
                name2 = "%s.%d" % (name, n)
                n += 1
            name = name2
        return Flowchart.createNode(self, nodeType, name=name, pos=pos)

    def configNodes(self):
        for i, spec in enumerate(self.layerList):
            node = self.nodeList[i]
            node.configFromLayerSpec(spec)

    def connectNodes(self):
        if self.holdUpdateConnects:
            return
        # connect node to first preceding node with same name
        for i, node in enumerate(self.nodeList[1:]):
            # iphase = node.phase()
            for iTerm in node.inputs().values():
                iname = iTerm.name()
                # iTerm.disconnectAll()
                # doBreak = False
                for previousNode in self.nodeList[i::-1]:
                    # ophase = previousNode.phase()
                    for output in previousNode.outputs().values():
                        oname = output.name()
                        assert isinstance(output, Terminal)
                        assert isinstance(iTerm, Terminal)
                        if iname == oname:
                            color = self.getConnectionColor(iTerm, previousNode)
                            # doBreak = True
                            #     color = self.getConnectionColor(iphase, ophase)
                            if color:

                                conItem = NetConnectionItem(iTerm.graphicsItem(), output.graphicsItem())
                                conItem.setStyle(color=color, shape='cubic')
                                iTerm.connectTo(output, conItem)
                                # self.connectTerminals(iTerm, output)
                                # break
                                # if doBreak:
                                #     break
        try:
            iTerm = self.nodeList[0].inputs().values()[0]
            self.connectTerminals(iTerm, self['dataIn'])
            output = self.nodeList[-1].outputs().values()[0]
            self.connectTerminals(output, self['dataOut'])
        except IndexError:
            self.hideInputs()

        self.updateProto()

    def getColorMapping(self, iphase, ophase):
        colorVal = None
        if iphase == ophase:
            colorVal = iphase
        elif iphase == -1:
            colorVal = ophase
        elif ophase == -1:
            colorVal = iphase
        return colorDict[colorVal]

    def getConnectionColor(self, iTerm, onode):
        # if input node is already connected to an output node of the same phase, do not connect
        iphase, ophase = iTerm.node().phase(), onode.phase()
        for connectedTerm in iTerm.connections().keys():
            if connectedTerm.node().phase() == ophase:
                return None
        return self.getColorMapping(iphase, ophase)

    def hideInputs(self):
        for node in [self.inputNode, self.outputNode]:
            node._allowRemove = True
            self.removeNode(node)

    def configNode(self, sender, action, node):
        if action == 'add':
            if isinstance(node, LayerNode):
                node.connectParamTree()
            elif isinstance(node, displayNodes):
                self.displayNodes[node.name()]=node
                self.sigDisplayNodeAdded.emit(node)
        if isinstance(node, LayerNode):
            self.netNeedsUpdate = True

    def updateProto(self):
        deps = {}
        # tdeps = {}   ## {terminal: [nodes that depend on terminal]}
        for name, node in self._nodes.items():
            if isinstance(node, LayerNode):
                deps[node] = node.dependentNodes()
            # for t in node.outputs().values():
            #     tdeps[t] = t.dependentNodes()

        # layerProto = LayerProto()
        try :
            sortedNodes = toposort.toposort_flatten(deps)
        except:
            print 'no valid net'
            return

        oldProto = NetProto()
        oldProto.CopyFrom(self.proto)

        self.proto.ClearField('layer')
        # self.proto.layer.Clear()
        self.proto.layer.extend([node.proto for node in sortedNodes])
        print oldProto == self.proto
        # self.proto.layer = layerProto
        # print self.proto

    def loadFile(self, fileName=None, startDir=None):
        if fileName is None:
            if startDir is None:
                startDir = self.filePath
            if startDir is None:
                startDir = '.'
            self.fileDialog = FileDialog(None, "Load Flowchart..", startDir, "Protobuf (*.prototxt)")
            #self.fileDialog.setFileMode(QtGui.QFileDialog.AnyFile)
            #self.fileDialog.setAcceptMode(QtGui.QFileDialog.AcceptSave)
            self.fileDialog.show()
            self.fileDialog.fileSelected.connect(self.loadFile)
            return
            ## NOTE: was previously using a real widget for the file dialog's parent, but this caused weird mouse event bugs..
            #fileName = QtGui.QFileDialog.getOpenFileName(None, "Load Flowchart..", startDir, "Flowchart (*.fc)")
        fileName = unicode(fileName)
        self.clear()
        self.proto = parsePrototxt(fileName, 'net')
        self.layerList = self.proto.layer
        self.initNodes()
        self.holdUpdateConnects = True
        self.configNodes()
        self.holdUpdateConnects = False
        self.connectNodes()
        self.viewBox.autoRange()
        #self.emit(QtCore.SIGNAL('fileLoaded'), fileName)
        self.sigFileLoaded.emit(fileName)

    def process(self, **args):
        # set needs update whenever net changes params
        # but don't let user change things like net dimensions
        if self.netNeedsUpdate:
            self.updateProto()
            # tempFile = NamedTemporaryFile()

            # for now make a nonTemp file so I can read it!
            tempFile = file('aprototxt.prototxt', 'w')

            # print str(self.proto)
            tempFile.write(str(self.proto))
            tempFile.close()
            netArgs = (tempFile.name, )
            # store the weights somewhere!
            if self.weights:
                netArgs += (self.weights, )
            # depends on tab? or is process only for test tab anyway?
            netArgs += (caffe.TEST, )
            self.net = caffe.Net(*netArgs)
            self.netNeedsUpdate = False
            self.netNeedsEval = True

        if self.netNeedsEval:
            kwargs = dict()
            if self.nextData is not None:
                kwargs['data'] = self.nextData
            self.net.forward(**kwargs)

        self.updatePlots()

    def updatePlots(self):
        # make a dictionary of terminals and their names
        blobsDict = {}
        # we want the terminals that provide the input for our displayNodes
        for nodeName, node in self.displayNodes.items():
            for inputName, inputTerm in node.inputs().items():
                for outputTerm in inputTerm.inputTerminals():
                    self.setNetTerminalData(outputTerm)

    def setNetTerminalData(self, term):
        blobName = term.name()
        netOutput = self.net.blobs[blobName].data
        term.setValue(netOutput)
        node = term.node()
        node.sigOutputChanged.emit(node)


    # get node

    # def widget(self):
    #     if self._widget is None:
    #         self._widget = LFlowchartCtrlWidget(self)
    #         self.scene = self._widget.scene()
    #         self.viewBox = self._widget.viewBox()
    #     return self._widget


colorDict = {-1:'w', 0:'r', 1:'b', None:None}

class LFlowchartWidget(FlowchartWidget):
    def __init__(self, *args, **kwargs):
        FlowchartWidget.__init__(self, *args, **kwargs)
#
# class LFlowchartCtrlWidget(FlowchartCtrlWidget):
#     def __init__(self, chart):
#         FlowchartCtrlWidget.__init__(self, chart)
#         self.ui.ctrlList = ParameterTree(self)
#         self.ui.ctrlList.setObjectName(_fromUtf8("ctrlList"))
#         self.ui.ctrlList.headerItem().setText(0, _fromUtf8("1"))
#         self.ui.ctrlList.header().setVisible(False)
#         self.ui.ctrlList.header().setStretchLastSection(False)
#         self.ui.gridLayout.addWidget(self.ui.ctrlList, 3, 0, 1, 4)
#
#         self.ui.ctrlList.setColumnCount(2)
#         #self.ui.ctrlList.setColumnWidth(0, 200)
#         self.ui.ctrlList.setColumnWidth(1, 20)
#         self.ui.ctrlList.setVerticalScrollMode(self.ui.ctrlList.ScrollPerPixel)
#         self.ui.ctrlList.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
#
#         self.ui.ctrlList.itemChanged.connect(self.itemChanged)
#
#     def addNode(self, node):
#         ctrl = node.ctrlWidget()
#         # if ctrl is None:
#         # return
#         if isinstance(node, Nodes.LayerNode):
#             item = node.param
#         else:
#             item = Parameter.create(name=node.name(),value=node.name())
#         self.ui.ctrlList.addParameters(item)
#         byp = QtGui.QPushButton('X')
#         byp.setCheckable(True)
#         byp.setFixedWidth(20)
#         item.bypassBtn = byp
#         # self.ui.ctrlList.setItemWidget(item, 1, byp)
#         byp.node = node
#         node.bypassButton = byp
#         byp.setChecked(node.isBypassed())
#         byp.clicked.connect(self.bypassClicked)
#
#         if ctrl is not None:
#             item2 = Parameter.create(name='wooo')
#             item.addChild(item2)
#             # self.ui.ctrlList.setItemWidget(item2, 0, ctrl)
#
#         self.items[node] = item


## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    import os

    app = QtGui.QApplication([])

    caffeDir = os.path.expanduser('~') + 'caffe/'
    model_dir = caffeDir + 'models/'
    rel_path = 'bvlc_reference_caffenet/train_val.prototxt'
    # rel_path = 'bvlc_reference_caffenet/deploy.prototxt'
    model_file = model_dir + rel_path

    win = QtGui.QMainWindow()
    win.resize(1200, 800)
    win.setWindowTitle('pyqtgraph example: Flowchart')
    cw = QtGui.QWidget()
    win.setCentralWidget(cw)
    layout = QtGui.QGridLayout()
    cw.setLayout(layout)
    # win.show()
    fc = NetFlowchart(model_file)
    fc.sigChartChanged.connect(fc.configNode)
    w = fc.widget()
    ctrlList = w.ui.ctrlList
    ctrlList.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    w.ui.ctrlList = ctrlList
    # w = w._nodes['LayerNode.0'].ctrlWidget()
    w.sizePolicy().setHorizontalPolicy(QtGui.QSizePolicy.MinimumExpanding)
    layout.addWidget(w)
    layout.addWidget(w.chartWidget, 0, 1)
    # w.chartWidget.moveDock()
    win.show()
    # fc.setNodes()
    # fc.connectNodes()

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
