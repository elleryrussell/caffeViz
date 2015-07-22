from pyqtgraph.flowchart.Flowchart import FlowchartWidget
from pyqtgraph.flowchart.Terminal import ConnectionItem, Terminal
from caffe.proto.caffe_pb2 import LayerParameter as LayerProto, NetParameter as NetProto

__author__ = 'ellery'

from pyqtgraph.flowchart import Flowchart
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
    def __init__(self, prototxt=None):
        self.nodeList = []
        Flowchart.__init__(self, terminals={
            'dataIn': {'io': 'in'},
            'dataOut': {'io': 'out'}
        })
        if prototxt is None:
            self.proto = NetProto()
            self.layerList = self.proto.layer
            self.plotList = {}
        else:
            self.proto = parseNetPrototxt(prototxt)
            self.layerList = self.proto.layer

        for proto in self.layerList:
            print proto
        self.setLibrary(Nodes.library)
        self.initNodes()

        fcw = self.widget().chartWidget
        fcw.viewDock.sizePolicy().setHorizontalPolicy(QtGui.QSizePolicy.Maximum)

        fcw.moveDock(fcw.hoverDock, 'right', fcw.viewDock)
        fcw.moveDock(fcw.selDock, 'bottom', fcw.hoverDock)


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
                # numeric suffix of layer
                try:
                    num = int(name[-1])
                except:
                    num = 0
                if lastNum != num:
                    ypos += 120
                    xpos = 0
                    # xpos += node.graphicsItem().bounds.width() + 20
                else:
                    xpos += 120
                lastNum = num
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

    def setNodes(self):
        for i, spec in enumerate(self.layerList):
            node = self.nodeList[i]
            node.configFromLayerSpec(spec)

    def connectNodes(self):
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

                                conItem = ConnectionItem(iTerm.graphicsItem(), output.graphicsItem())
                                conItem.setStyle(color=color)
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
            node.connectParamTree()

    def updateProto(self):
        layerProto = LayerProto()
        layerProto.extend([node.proto for node in self.nodes()])
        self.proto.layer = layerProto


colorDict = {-1:'w', 0:'r', 1:'b', None:None}

class LFlowchartWidget(FlowchartWidget):
    def __init__(self, *args, **kwargs):
        FlowchartWidget.__init__(self, *args, **kwargs)



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
    # for item in ctrlList.
    ctrlList.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    w.ui.ctrlList = ctrlList
    # w = w._nodes['LayerNode.0'].ctrlWidget()
    w.sizePolicy().setHorizontalPolicy(QtGui.QSizePolicy.MinimumExpanding)
    layout.addWidget(w)
    layout.addWidget(w.chartWidget, 0, 1)
    # w.chartWidget.moveDock()
    win.show()
    fc.setNodes()
    fc.connectNodes()

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
