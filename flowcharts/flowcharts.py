__author__ = 'ellery'

from pyqtgraph.flowchart import Flowchart
from pyqtgraph.Qt import QtGui, QtCore
from google.protobuf import text_format
import caffe

from nodes import Nodes


def _readProtoNetFile(filepath):
    solver_config = caffe.proto.caffe_pb2.NetParameter()

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

    return netPB.layer


class NetFlowchart(Flowchart):
    def __init__(self, prototxt=None):
        Flowchart.__init__(self, terminals={
            'dataIn': {'io': 'in'},
            'dataOut': {'io': 'out'}
        })
        if prototxt is None:
            self.layerList = None
            self.plotList = {}
        else:
            self.layerList = parseNetPrototxt(prototxt)
        self.nodeList = []
        self.setLibrary(Nodes.library)
        self.setupNodes()
        # self.connectNodes()

    def setupNodes(self):
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
                node.configFromLayerSpec(layerParam)
                # node.sigRenamed.connect(self.nodeRenamed)
                self.nodeList.append(node)
            ypos += 150
            self.outputNode.graphicsItem().setPos(xpos, 0)
        else:
            # default node config
            node = self.createNode("LayerNode")

    def connectNodes(self):
        # connect node to first preceding node with same name
        for i, node in enumerate(self.nodeList[1:]):
            for iname, input in node.inputs().items():
                doBreak = False
                for previousNode in self.nodeList[i::-1]:
                    for oname, output in previousNode.outputs().items():
                        if iname in oname:
                            doBreak = True
                            self.connectTerminals(input, output)
                            break
                    if doBreak:
                        break
        try:
            input = self.nodeList[0].inputs().values()[0]
            self.connectTerminals(input, self['dataIn'])
            output = self.nodeList[-1].outputs().values()[0]
            self.connectTerminals(output, self['dataOut'])
        except IndexError:
            self.hideInputs()

    def hideInputs(self):
        for node in [self.inputNode, self.outputNode]:
            node._allowRemove = True
            self.removeNode(node)


## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys

    app = QtGui.QApplication([])

    model_dir = '/home/ellery/caffe/models/'
    rel_path = 'bvlc_reference_caffenet/train_val.prototxt'
    # rel_path = 'bvlc_reference_caffenet/deploy.prototxt'
    model_file = model_dir + rel_path

    win = QtGui.QMainWindow()
    win.resize(600, 800)
    win.setWindowTitle('pyqtgraph example: Flowchart')
    cw = QtGui.QWidget()
    win.setCentralWidget(cw)
    layout = QtGui.QGridLayout()
    cw.setLayout(layout)
    fc = NetFlowchart(model_file)
    w = fc.widget()
    ctrlList = w.ui.ctrlList
    # for item in ctrlList.
    ctrlList.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    w.ui.ctrlList = ctrlList
    # w = w._nodes['LayerNode.0'].ctrlWidget()
    layout.addWidget(w)
    win.show()
    fc.connectNodes()

    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
