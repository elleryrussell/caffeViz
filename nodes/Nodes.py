from caffe.proto.caffe_pb2 import LayerParameter as LayerProto, NetParameter, V1LayerParameter
from caffe import Layer
from google.protobuf.internal.containers import RepeatedCompositeFieldContainer

import customParameterTypes
from customParameterTypes import LParameter

__author__ = 'ellery'

# from caffe.proto import caffe_pb2
from caffe.net_spec import _param_names

_param_names['Deconvolution']='convolution'

from pyqtgraph.flowchart import Node
import pyqtgraph.flowchart.library as fclib
import pyqtgraph.parametertree as ptree
from utils import slotDisconnected, signalsBlocked
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg

# import numpy as np

class LayerNode(Node):
    """PsuedoNode for caffe layer"""

    generalParams = LayerProto
    nodeName = "LayerNode"
    sigProtoChanged = QtCore.Signal(object)

    def __init__(self, name):
        Node.__init__(self, name, allowAddInput=True, allowAddOutput=True, allowRemove=True)
        # self.paramList = self.getParamList()
        LayerFD = NetParameter.DESCRIPTOR.fields_by_name['layer']
        self.param = LParameter.create(repeated=False, fieldDescriptor=LayerFD, expanded=True)
        for param in self.param.children():
            param.setToDefault()
        t = ptree.ParameterTree()
        t.addParameters(self.param, depth=1, showTop=False)
        self.proto = LayerProto()
        self.specificParam = None
        self.baseParam = None
        self.sigRenamed.connect(self.nameChanged)
        self.sigTerminalRenamed.connect(self.updateBlobs)
        self.sigTerminalAdded.connect(self.updateBlobs)
        self.sigTerminalRemoved.connect(self.updateBlobs)
        t.setMinimumHeight(325)
        t.setVerticalScrollBarPolicy(pg.QtCore.Qt.ScrollBarAlwaysOff)
        self.ui = t

        self.bottoms = self.param.child('bottom')
        self.tops = self.param.child('top')
        # self.bottoms.sigChildAdded.connect(self.updateTerminals)
        # self.tops.sigChildAdded.connect(self.updateTerminals)

        if self.nodeName != "LayerNode":
            proto = LayerProto()
            proto.type = self.nodeName
            self.configFromLayerSpec(proto)
            self.param.child('bottom').addNew()
            self.param.child('top').addNew()

    def ctrlWidget(self):
        return self.ui

    # def process(self, dataIn, display=True):
    #     # CtrlNode has created self.ctrls, which is a dict containing {ctrlName: widget}
    #     sigma = self.ctrls['sigma'].value()
    #     strength = self.ctrls['strength'].value()
    #     output = dataIn - (strength * pg.gaussianFilter(dataIn, (sigma, sigma)))
    #     return {'dataOut': output}
    #
    # def getParamList(self):
    #     fieldDescriptors = [field for field in self.generalParams().DESCRIPTOR.fields if '_param' not in field.name]
    #     return [makeParamList(fd) for fd in fieldDescriptors]

    def configFromLayerSpec(self, layerSpec):
        print layerSpec
        # get type for specific param
        self.proto = layerSpec
        assert isinstance(layerSpec, (LayerProto, V1LayerParameter))
        layerType = layerSpec.type

        if isinstance(layerSpec, V1LayerParameter):
            enumVals = layerSpec.DESCRIPTOR.enum_types_by_name['LayerType'].values_by_number
            typeName = enumVals[layerType].name
            self.updateSpecificParam(typeName.capitalize())
        else:
            self.updateSpecificParam(layerType)

        self.updateParamList(self.proto)
        self.updateTerminals()
        self.connectParamTree()

        self.updateProto()

    def connectParamTree(self):
        self.param.sigTreeStateChanged.connect(self.paramTreeChanged)
        self.param.sigTreeStateChanged.connect(self.updateProto)

    def updateParamList(self, layerSpec):
        self.param.setValue(layerSpec)

    def updateTerminals(self):
        with slotDisconnected(self.sigTerminalRemoved, self.updateBlobs):
            self.clearTerminals()
        with slotDisconnected(self.sigTerminalAdded, self.updateBlobs):
            # try:
            for interm in self.bottoms.value():
                self.addInput(name=interm)
            for outterm in self.tops.value():
                self.addOutput(name=outterm)

    def addInput(self, name="Input", **args):
        args.update(multi=True)
        Node.addInput(self, name=name, **args)

    # def addOutput(self, name="Output", **args):
    #     Node.addOutput(self, name=name, **args)

    def addTerminal(self, name, **opts):
        opts.update(renamable=True, removable=True)
        Node.addTerminal(self, name, **opts)

    def paramTreeChanged(self, topParam, changes):
        for childParam, change, value in changes:
            if childParam.name() == 'name' and childParam.parent() is topParam:
                if value is None:
                    value = ''
                self.graphicsItem().nameItem.setPlainText(pg.QtCore.QString(value))
                with slotDisconnected(self.sigRenamed, self.nameChanged):
                    self.rename(str(value))
            elif childParam.name() == 'type':
                self.updateSpecificParam(value)
            elif 'bottom' in childParam.name() or 'top' in childParam.name():
                self.updateTerminals()

    def updateProto(self):
        layerSpec = LayerProto()
        for param in self.param.children():
            assign_proto(layerSpec, param)
        # print layerSpec
        self.proto = layerSpec
        self.sigProtoChanged.emit(self)

    def nameChanged(self):
        with signalsBlocked(self.param):
            nameParam = self.param.child('name')
            nameParam.setValue(self.name())

    def updateBlobs(self):
        with signalsBlocked(self.param):
            inputs = self.inputs()
            self.bottoms.setValue([i for i in inputs], clear=True)
            outputs = self.outputs()
            self.tops.setValue([o for o in outputs], clear=True)

    def updateSpecificParam(self, layerType):
        layerSpec = self.proto
        try:
            specifcParamName = _param_names[layerType] + '_param'
            specificFieldDescriptor = layerSpec.DESCRIPTOR.fields_by_name[specifcParamName]
            child = LParameter.create(fieldDescriptor=specificFieldDescriptor)
            # add specific parameter type to top level param
            if self.specificParam is not None:
                self.param.removeChild(self.specificParam)
            self.specificParam = self.param.insertChild(4, child)
            self.specificParam.setToDefault()
        except KeyError:
            pass
        if self.baseParam is not None:
            self.param.removeChild(self.baseParam)

        if layerType == 'Data':
            additionalParamName = 'transform_param'
            self.addAdditionalParam(additionalParamName)

        if 'Loss' in layerType:
            additionalParamName = 'loss_param'
            self.addAdditionalParam(additionalParamName)

    def addAdditionalParam(self, name):
        additionalFieldDescriptor = self.proto.DESCRIPTOR.fields_by_name[name]
        child = LParameter.create(fieldDescriptor=additionalFieldDescriptor)
        self.baseParam = self.param.insertChild(5, child)

    def phase(self):
        includeChildren = self.param.child('include').children()
        if len(includeChildren) > 0:
            # FIXME do i need all the children's phases?
            includeChild = includeChildren[0]
            return includeChild.child('phase').value()
        return self.param.child('phase').value()


"Allowed Types"
LayerTypes = ['AbsVal', 'Accuracy', 'ArgMax', 'BNLL', 'Concat', 'ContrastiveLoss', 'Convolution', 'Data',
              'Deconvolution', 'Dropout', 'DummyData', 'Eltwise', 'EuclideanLoss', 'Exp', 'Filter', 'Flatten',
              'HDF5Data', 'HDF5Output', 'HingeLoss', 'Im2col', 'ImageData', 'InfogainLoss', 'InnerProduct', 'LRN',
              'Log', 'MVN', 'MemoryData', 'MultinomialLogisticLoss', 'PReLU', 'Pooling', 'Power', 'Python', 'ReLU',
              'Reduction', 'Reshape', 'SPP', 'Sigmoid', 'SigmoidCrossEntropyLoss', 'Silence', 'Slice', 'Softmax',
              'SoftmaxWithLoss', 'Split', 'TanH', 'Threshold', 'WindowData', 'Crop']


# def generateProto(self, proto, param):
#     """
#     write a LayerParameter message for this layer, based upon the types of the parameters in this node's parameterTree
#     :return: message containing all non-default fields for this layer
#     """
#     currentMessage = self.layerSpec
#
#
#     for param in self.param.children():
#         if param.type == 'group':
#             layerSpec.getattr((generateProto(param))
#         elif param.isDefault():
#             pass
#         else
#

def assign_proto(proto, param):
    """Assign a Python object to a protobuf message, based on the Python
    type (in recursive fashion). Lists become repeated fields/messages, dicts
    become messages, and other types are assigned directly."""

    # repeated fields type
    if param.type() == 'repeated':
        if param.valueIsDefault():
            return
        # if hasattr(param, 'addList'):
        children = param.children()
        # message type
        for child in children:
            if child.type() == 'message':
                proto_item = getattr(proto, param.name()).add()
                for grandchild in child.children():
                    assign_proto(proto_item, grandchild)
            elif not child.valueIsDefault():
                getattr(proto, param.name()).extend([child.value()])
                # message type
    elif param.type() == 'message':
        for childParam in param.children():
            assign_proto(getattr(proto, param.name()), childParam)
    elif param.valueIsDefault():
        return proto
    elif param.type() == 'list':
        setattr(proto, param.name(), param.value())
    # any other type
    else:
        setattr(proto, param.name(), param.value())
        # default = param.defaultValue(), param.value()
        # print default
        # print proto
        # return proto


library = fclib.LIBRARY.copy()
library.addNodeType(LayerNode, [('Layers',)])

for layerType in LayerTypes:
    class ANode(LayerNode):
        nodeName = layerType
    library.addNodeType(ANode, [('Layers',)])

# layerTypes =

typeDict = {
    1: 'int',
    2: 'int',
    3: 'int',
    4: 'int',
    5: 'double',
    6: 'float',
    7: 'bool',
    8: 'enum',
    9: 'str',
    10: 'message'}

from pyqtgraph import QtGui

if __name__ == '__main__':
    pg.mkQApp()
    win = QtGui.QMainWindow()
    w = LayerNode('anode')
    win.setCentralWidget(w.ui)
    win.show()
    QtGui.QApplication.instance().exec_()
    print 'here'
