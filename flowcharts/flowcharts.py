from pyqtgraph.flowchart.Flowchart import Flowchart, FlowchartWidget, FlowchartCtrlWidget, FlowchartCtrlTemplate
from pyqtgraph.flowchart.FlowchartCtrlTemplate_pyqt import _fromUtf8
from pyqtgraph.flowchart.Terminal import ConnectionItem, Terminal
from NetTerminal import NetConnectionItem
from pyqtgraph.parametertree import ParameterTree, Parameter
from caffe.proto.caffe_pb2 import LayerParameter as LayerProto, NetParameter as NetProto
from pyqtgraph.functions import toposort

import inspect

from pyqtgraph.flowchart.library import Display
displayNodes = tuple(obj for name, obj in inspect.getmembers(Display) if inspect.isclass(obj))

from pyqtgraph.widgets.FileDialog import FileDialog

import sip
from nodes.Nodes import LayerNode

__author__ = 'ellery'

from pyqtgraph.Qt import QtGui, QtCore
from google.protobuf import text_format
import caffe

from nodes import Nodes


def _readProtoNetFile(filepath):
    solver_config = NetProto()

    return _readProtoFile(filepath, solver_config)


def _readProtoFile(filepath, parser_object):
    file = open(filepath, "r")

    if not file:
        raise NameError("ERROR (" + filepath + ")!")

    text_format.Merge(str(file.read()), parser_object)
    file.close()
    return parser_object


def parseNetPrototxt(filename):
    """return a list of layers and their (perhaps nested) fields to initialize Nodes """
    netPB = _readProtoNetFile(filename)
    # all of the layer messages

    return netPB


class NetFlowchart(Flowchart):
    sigDisplayNodeAdded = QtCore.Signal(object) # node

    def __init__(self, prototxt=None, weights=None):
        self.nodeList = []
        self.holdUpdateConnects = True
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
            self.proto = parseNetPrototxt(prototxt)
            self.layerList = self.proto.layer
            # for old proto
            if len(self.layerList)==0:
                self.layerList = self.proto.layers

        self.weights = weights

        for proto in self.layerList:
            print proto
        self.setLibrary(Nodes.library)
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
                node = self.createNode("LayerNode", name=name, pos=(xpos, ypos))
                # node.configFromLayerSpec(layerParam)
                # node.configFromLayerSpec(layerParam)
                # node.sigRenamed.connect(self.nodeRenamed)
                self.nodeList.append(node)
            ypos += 150
            self.outputNode.graphicsItem().setPos(xpos, 0)
        else:
            # default node config
            node = self.createNode("LayerNode")

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
            for iname, iTerm in node.inputs().items():
                # iTerm.disconnectAll()
                # doBreak = False
                for previousNode in self.nodeList[i::-1]:
                    # ophase = previousNode.phase()
                    for oname, output in previousNode.outputs().items():
                        assert isinstance(output, Terminal)
                        assert isinstance(iTerm, Terminal)
                        if iname in oname:
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
                self.sigDisplayNodeAdded.emit(node)

    def updateProto(self):
        deps = {}
        # tdeps = {}   ## {terminal: [nodes that depend on terminal]}
        for name, node in self._nodes.items():
            deps[node] = node.dependentNodes()
            # for t in node.outputs().values():
            #     tdeps[t] = t.dependentNodes()

        # layerProto = LayerProto()
        try :
            sortedNodes = toposort(deps)
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
        self.proto = parseNetPrototxt(fileName)
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
            netArgs = (self.proto, )
            # store the weights somewhere!
            if self.weights:
                netArgs += (self.weights)
            # depends on tab? or is process only for test tab anyway?
            netArgs += caffe.TEST
            self.net = caffe.Net(*netArgs)

        blobs = []

        # make a dictionary of terminals and their names
        # we want the terminals that provide the input for our displayNodes

        blobsDict = {}
        for node in self.displayNodes:
            for inputTerm in node.inputs():
                for outputTerm in inputTerm.inputTerminals():
                    blobName = outputTerm.name
                    blobsDict[blobName] = outputTerm

        kwargs = dict(blobs=blobsDict.keys())
        if self.nextData:
            kwargs['data']=self.nextData
        netOutputs = self.net.forward(**kwargs)

        # then we take the blobs from netOutputs and set the corresponding terminal to their value
        for blobName, outputTerm in blobsDict.items():
            outputTerm.setValue(netOutputs[blobName])


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

    app = QtGui.QApplication([])

    model_dir = '/Users/err258/caffe/models/'
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
