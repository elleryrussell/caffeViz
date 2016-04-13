from pyqtgraph import configfile
from pyqtgraph.flowchart.Flowchart import Flowchart
from caffe.proto.caffe_pb2 import NetParameter as NetProto
import toposort
from pyqtgraph.flowchart.library import getNodeTree

from caffeViz.netTerminal import NetConnectionItem, NetTerminal
from caffeViz.protobufUtils import parsePrototxt

displayNodes = tuple(getNodeTree()['Display'].values())

from pyqtgraph.widgets.FileDialog import FileDialog

from caffeViz.nodes.LayerNodes import LayerNode

__author__ = 'ellery'

from pyqtgraph.Qt import QtGui, QtCore
import caffe


class NetFlowchart(Flowchart):
    """An extension of pyqtgraph's flowchart for Caffe-based Neural Nets"""

    sigDisplayNodeAdded = QtCore.Signal(object)  # node

    def __init__(self, prototxt=None, weights=None):
        """
        A flowchart that enables visualizing, editing, and running a caffe neural network model

        :param prototxt: string
            Optional path to a caffe prototxt file, which will be used as the initial model for the network
        :param weights: string
            Optional path to a caffe caffemodel file, which will be used as the initial weights for the network
        """

        self.nodeList = []
        self.displayNodes = {}
        self.netNeedsUpdate = True
        self.netNeedsEval = True
        self.holdUpdateConnects = True
        self.nextData = None
        Flowchart.__init__(self, terminals={
            'dataIn': {'io': 'in'},
            'dataOut': {'io': 'out'}
        })

        if prototxt is None:
            self.proto = NetProto()
            self.layerList = self.proto.layer
            self.plotList = {}
        else:
            self.proto = parsePrototxt(prototxt, 'net')
            self.layerList = self.proto.layer
            # for old proto format
            if len(self.layerList) == 0:
                self.layerList = self.proto.layers

        self.weights = weights

        for proto in self.layerList:
            print proto

        self.setupNodes()

        fcw = self.widget().chartWidget
        fcw.viewDock.sizePolicy().setHorizontalPolicy(QtGui.QSizePolicy.Maximum)

        fcw.moveDock(fcw.hoverDock, 'bottom', fcw.viewDock)
        fcw.moveDock(fcw.selDock, 'right', fcw.hoverDock)

    def setupNodes(self):
        """
        perform the necessary setup
        """
        self.createAndLayoutNodes()
        self.holdUpdateConnects = True
        self.configureNodes()
        self.holdUpdateConnects = False
        self.connectNodes()
        self.viewBox.autoRange()

    def clear(self):
        self.nodeList = []
        Flowchart.clear(self)

    def createAndLayoutNodes(self):
        """
        Create all the nodes and lay them out in the flowchart
        """

        nodeSize = 200
        spacingSize = int(nodeSize * 1.1)

        # layout the nodes in a somewhat sensible fashion based upon the numbers used in the names
        # could be a lot more
        if self.layerList:
            ypos, xpos = 0, -spacingSize
            lastNum = 1
            for i, layerParam in enumerate(self.layerList):
                name = str(layerParam.name).lower()

                digits = [int(s) for s in name if s.isdigit()]
                if len(digits) == 0:
                    primaryDigit = 0
                else:
                    primaryDigit = digits[0]
                # numeric suffix of layer
                if lastNum != primaryDigit:
                    ypos += spacingSize
                    xpos = 0
                    # xpos += node.graphicsItem().bounds.width() + 20
                else:
                    xpos += spacingSize
                lastNum = primaryDigit
                node = self.createNode("Layer", name=name, pos=(xpos, ypos))
                self.nodeList.append(node)
            ypos += 150
            self.outputNode.graphicsItem().setPos(xpos, 0)
        else:
            # default node config
            node = self.createNode("Layer")

    def createNode(self, nodeType, name=None, pos=None):
        """
        overrides Flowchart.createNode to pick sensible names that caffe will accept
        """
        if name is None:
            name = nodeType.lower()
        if name in self._nodes:
            name2 = name
            n = 1
            while name2 in self._nodes:
                name2 = "%s.%d" % (name, n)
                n += 1
            name = name2
        return Flowchart.createNode(self, nodeType, name=name, pos=pos)

    def configureNodes(self):
        """run through self.layerList attribute and configure all the nodes from their caffe layerSpec"""
        for i, spec in enumerate(self.layerList):
            node = self.nodeList[i]
            node.configFromLayerSpec(spec)

    def connectNodes(self):
        """run through the nodeList attribute, connecting all the terminals of the nodes based on their names"""
        if self.holdUpdateConnects:
            return

        # connect node to first preceding node with same name
        for i, node in enumerate(self.nodeList[1:]):
            for inTerm in node.inputs().values():
                inName = inTerm.name()
                # work backward to find the first node with the correct output terminal (there can be more than one)
                for previousNode in self.nodeList[i::-1]:
                    for outTerm in previousNode.outputs().values():
                        outName = outTerm.name()
                        if inName == outName:
                            color = self.getConnectionColor(inTerm, previousNode)
                            if color is not None:
                                conItem = NetConnectionItem(inTerm.graphicsItem(), outTerm.graphicsItem())
                                conItem.setStyle(color=color, shape='cubic')
                                try:
                                    assert isinstance(inTerm, NetTerminal)
                                    inTerm.connectTo(outTerm, conItem, rename=False)
                                except TypeError:
                                    inTerm.connectTo(outTerm, conItem)
        try:
            # try and link up the flowchart's input and output to the node network, but this can fail depending on the
            # type of input nodes
            inTerm = self.nodeList[0].inputs().values()[0]
            self.connectTerminals(inTerm, self['dataIn'])
            outTerm = self.nodeList[-1].outputs().values()[0]
            self.connectTerminals(outTerm, self['dataOut'])
        except IndexError:
            self.hideInputs()

        self.updateProto()

    def getConnectionColor(self, inTerm, outNode):
        """
        get the color for the node connection based on the phases of the inputs
        :param inTerm: Terminal
            The input terminal
        :param outNode: Node
            the output Node
        """
        outPhase = outNode.phase()
        # if input node is already connected to an output node of the same phase, do not connect
        for connectedTerm in inTerm.connections().keys():
            if connectedTerm.node().phase() == outPhase:
                return None
        inPhase = inTerm.node().phase()
        return self.getColorMapping(inPhase, outPhase)

    @staticmethod
    def getColorMapping(inPhase, outPhase):
        """
        get the color mapping based on the phases of the input and output
        :param inPhase: int
            the input phase
        :param outPhase: int
            the output phase
        """
        colorVal = None
        if inPhase == outPhase:
            colorVal = inPhase
        elif inPhase == -1:
            colorVal = outPhase
        elif outPhase == -1:
            colorVal = inPhase
        return colorDict[colorVal]

    def hideInputs(self):
        for node in [self.inputNode, self.outputNode]:
            node._allowRemove = True
            self.removeNode(node)

    def chartNodeEdited(self, sender, action, node):
        """
        configure a node
        :param sender: QObject, not used
        :param action: str
            name of the action
        :param node: Node
            node object that the action was performed on
        """
        if action == 'add':
            if isinstance(node, LayerNode):
                node.connectParamTree()
            elif isinstance(node, displayNodes):
                self.displayNodes[node.name()] = node
                self.sigDisplayNodeAdded.emit(node)
        if isinstance(node, LayerNode):
            self.netNeedsUpdate = True

    def updateProto(self):
        """
        update the Prototxt file for the entire net based upon the Flowchart's LayerNodes
        """
        deps = {}
        for name, node in self._nodes.items():
            if isinstance(node, LayerNode):
                deps[node] = node.dependentNodes()
        try:
            sortedNodes = toposort.toposort_flatten(deps)
        except StandardError as e:
            print 'no valid net'
            print e
            return

        # oldProto = NetProto()
        # oldProto.CopyFrom(self.proto)

        self.proto.ClearField('layer')
        self.proto.layer.extend([node.proto for node in sortedNodes])
        return self.proto

    def loadFile(self, fileName=None, startDir=None):
        """load a new prototxt file"""
        if fileName is None:
            if startDir is None:
                startDir = self.filePath
            if startDir is None:
                startDir = '.'
            self.fileDialog = FileDialog(None, "Load Flowchart..", startDir, "Protobuf (*.prototxt)")
            self.fileDialog.show()
            self.fileDialog.fileSelected.connect(self.loadFile)
            return
        fileName = unicode(fileName)
        self.clear()
        self.proto = parsePrototxt(fileName, 'net')
        self.layerList = self.proto.layer

        self.setupNodes()
        self.sigFileLoaded.emit(fileName)

    def saveFile(self, fileName=None, startDir=None, suggestedFileName='flowchart.fc'):
        """save the current prototxt file"""
        if fileName is None:
            if startDir is None:
                startDir = self.filePath
            if startDir is None:
                startDir = '.'
            self.fileDialog = FileDialog(None, "Save Flowchart..", startDir, "Flowchart (*.fc)")
            self.fileDialog.setAcceptMode(QtGui.QFileDialog.AcceptSave)
            self.fileDialog.show()
            self.fileDialog.fileSelected.connect(self.saveFile)
            return
        fileName = unicode(fileName)
        configfile.writeConfigFile(self.saveState(), fileName)
        self.sigFileSaved.emit(fileName)

    def process(self, forward=False, **args):
        """
        Respond to the flowchart's request to process
        :param forward: whether to process the next data or reprocess current data
        """
        # set needs update whenever net changes params
        # but don't let user change things like net dimensions
        if self.netNeedsUpdate:
            self.getCaffeNet()

        if self.netNeedsEval or forward:
            kwargs = dict()
            if self.nextData is not None:
                kwargs['data'] = self.nextData
            self.net.forward(**kwargs)
            self.netNeedsEval = False

        self.updatePlots()

    def getCaffeNet(self):
        """
        load a caffe Net object based on the updated protocol buffer
        :return:
        """
        proto = self.updateProto()
        # tempFile = NamedTemporaryFile()

        # for now make a nonTemp file so I can read it!
        tempFile = file('aprototxt.prototxt', 'w')

        # print str(self.proto)
        tempFile.write(str(proto))
        tempFile.close()
        netArgs = (tempFile.name,)
        # store the weights somewhere!
        if self.weights:
            netArgs += (self.weights,)
        # depends on tab? or is process only for test tab anyway?
        netArgs += (caffe.TEST,)
        self.net = caffe.Net(*netArgs)
        self.netNeedsUpdate = False
        self.netNeedsEval = True

    def updatePlots(self):
        """run through the display nodes and update the immediately preceding LayerNodes from the caffe net data"""
        # we want the terminals that provide the input for our displayNodes
        for nodeName, node in self.displayNodes.items():
            for inputName, inputTerm in node.inputs().items():
                for outputTerm in inputTerm.inputTerminals():
                    self.setNetTerminalData(outputTerm)

    def setNetTerminalData(self, term):
        """
        pulls the data from the caffe net's blob with the corresponding name and sets the terminal's data to this value,
        which will cause any dependent Display nodes to update their displays
        :param term: NetTerminal
        """
        blobName = term.name()
        netOutput = self.net.blobs[blobName].data
        term.setValue(netOutput)
        node = term.node()
        node.sigOutputChanged.emit(node)


# mapping between phases and colors
# -1, is both, 0 is test, 1 is deploy
colorDict = {-1: 'w', 0: 'r', 1: 'b', None: None}


# class LFlowchartWidget(FlowchartWidget):
#     """Overriding the FlowchartWidget's hoverOver method"""
#
#     def hoverOver(self, items):
#         # print "FlowchartWidget.hoverOver called."
#         term = None
#         layerNode = None
#         for item in items:
#             if item is self.hoverItem:
#                 return
#             self.hoverItem = item
#             if hasattr(item, 'term') and isinstance(item.term, Terminal):
#                 term = item.term
#                 break
#             elif isinstance(item, LayerNode):
#                 layerNode = item
#         if term is None and layerNode is None:
#             txt = ""
#         elif layerNode is None:
#             val = term.value()
#             if isinstance(val, ndarray):
#                 val = "%s %s %s" % (type(val).__name__, str(val.shape), str(val.dtype))
#             else:
#                 val = str(val)
#                 if len(val) > 400:
#                     val = val[:400] + "..."
#             txt = "%s.%s = %s" % (term.node().name(), term.name(), val)
#         else:
#             val = layerNode.proto
#             if len(val) > 400:
#                 val = val[:400] + "..."
#             txt = "%s.proto = %s" % (layerNode.name(), val)
#         self.hoverText.setPlainText(txt)


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
    fc.sigChartChanged.connect(fc.chartNodeEdited)
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
