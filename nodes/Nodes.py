from caffe.proto.caffe_pb2 import LayerParameter as LayerProto
from google.protobuf.internal.containers import RepeatedCompositeFieldContainer

import customParameterTypes
from customParameterTypes import LParameter

__author__ = 'ellery'

# from caffe.proto import caffe_pb2
from caffe.net_spec import _param_names

from pyqtgraph.flowchart import Node
import pyqtgraph.flowchart.library as fclib
import pyqtgraph.parametertree as ptree
# from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
# import numpy as np

class LayerNode(Node):
    """PsuedoNode for caffe layer"""

    generalParams = LayerProto
    nodeName = "LayerNode"

    def __init__(self, name):
        Node.__init__(self, name)
        # self.paramList = self.getParamList()
        self.param = LParameter.create(name='LayerParameter', fieldDescriptor=LayerProto)
        for param in self.param.children():
            param.setToDefault()
        t = ptree.ParameterTree()
        t.addParameters(self.param, depth=1, showTop=False)
        self.layerSpec = LayerProto
        self.specificParam = None
        self.baseParam = None
        self.blockRename = False
        self.sigRenamed.connect(self.nameChanged)
        t.setMinimumHeight(325)
        t.setVerticalScrollBarPolicy(pg.QtCore.Qt.ScrollBarAlwaysOff)
        self.ui = t

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
        self.layerSpec = layerSpec
        assert isinstance(layerSpec, LayerProto)
        layerType = layerSpec.type

        self.updateSpecificParam(layerType)

        self.updateParamList(self.layerSpec)
        self.updateTerminals()
        self.param.sigTreeStateChanged.connect(self.paramTreeChanged)

    def updateParamList(self, layerSpec, path=()):
        # replace this all with self.param.setValue(layerSpec)


        if not isinstance(layerSpec, (RepeatedCompositeFieldContainer)):
            layerSpec = [layerSpec]
        for spec in layerSpec:
            for field, value in spec.ListFields():
                childPath = (field.name,)
                for parent in path:
                    childPath = (parent,) + childPath
                param = self.param.child(*childPath)
                if isinstance(param, ptree.types.SimpleParameter):
                    if field.cpp_type == 9:
                        if isinstance(value, unicode):
                            value = str(value)
                    param.setValue(value)
                elif isinstance(param, customParameterTypes.LRepeatedParameter):
                    for val in value:
                        typ = typeDict[field.cpp_type]
                        if typ == 'message':
                            # typ = 'group'
                            # let the custom param handle this?
                            childParam = param.addNew(value=field.message_type.fields)
                            newPath = [childParam.name(), field.name] + list(path)
                            self.updateParamList(val, path=newPath)
                        else:
                            param.addNew(value=val)
                elif isinstance(param, ptree.types.GroupParameter):
                    newPath = [field.name] + list(path)
                    self.updateParamList(value, path=newPath)

    def updateTerminals(self):
        self.clearTerminals()
        bottom = self.param.child('bottom')
        try:
            for interm in self.param.child('bottom').value():
                self.addInput(name=interm)
            for outterm in self.param.child('top').value():
                self.addOutput(name=outterm)
        except:
            pass

    # def updateProto(self):
    #     # self.layerSpec = layerSpec

    def paramTreeChanged(self, topParam, changes):
        for childParam, change, value in changes:
            if childParam.name() == 'name' and childParam.parent() is topParam:
                if value is None:
                    value = ''
                self.graphicsItem().nameItem.setPlainText(pg.QtCore.QString(value))
                # self.blockSignals(True)
                self.blockRename = True
                self.rename(str(value))
                self.blockRename = False
                # self.blockSignals(False)
            elif childParam.name() == 'type':
                self.updateSpecificParam(value)
        layerSpec = LayerProto
        for param in self.param.children():
            assign_proto(layerSpec, param)
            print layerSpec

    def nameChanged(self):
        if not self.blockRename:
            nameParam = self.param.child('name')
            # self.param.blockSignals(True)
            nameParam.setValue(self.name())
            # self.param.blockSignals(False)

    def updateSpecificParam(self, layerType):
        layerSpec = self.layerSpec
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
        additionalFieldDescriptor = self.layerSpec.DESCRIPTOR.fields_by_name[name]
        child = LParameter.create(fieldDescriptor=additionalFieldDescriptor)
        self.baseParam = self.param.insertChild(5, child)


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
    if param.type() == 'layerGroup':
        if param.valueIsDefault():
            return
        # if hasattr(param, 'addList'):
        children = param.children()
        # message type
        for child in children:
            if child.type() == 'group' or child.type() == 'message':
                proto_item = getattr(proto, param.name()).add()
                for grandchild in child.children():
                    assign_proto(proto_item, grandchild)
            else:
                getattr(proto, param.name()).extend([child.value() for child in children if not child.valueIsDefault()])
                # message type
    elif param.type() == 'group' or param.type() == 'message':
        for childParam in param.children():
            assign_proto(getattr(proto, param.name()), childParam)
    elif param.valueIsDefault():
        return proto
    elif param.type() == 'list':
        setattr(proto, param.name(), param.value())
    # any other type
    else:
        setattr(proto, param.name(), param.value())
    default = param.defaultValue(), param.value()
    # print default
    # print proto
    # return proto


library = fclib.LIBRARY.copy()
library.addNodeType(LayerNode, [('Layers',)])

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

# def makeParamList(fd, value=None):
#     # name = fd.name
#     ftype = typeDict[fd.cpp_type]
#
#     if ftype == 'enum':
#         opts = {'type': 'list', 'limits': {value.name:value.number for value in fd.enum_type.values}}
#         if not fd.has_default_value:
#             opts['limits']
#     # repeated field container
#     elif fd.label == 3:
#         opts = {'type': 'layerGroup', 'addText': 'add', 'field': fd, 'subTyp':ftype}
#         # if ftype == 'message':
#             # subParamList = [makeParamList(mfield) for mfield in fd.message_type.fields]
#             # opts['subParamList'] = subParamList
#     elif ftype == 'message':
#         opts = {'type': ftype, 'value': [makeParamList(mfield) for mfield in fd.message_type.fields]}
#     else:
#         opts = {'type': ftype}
#
#     if fd.has_default_value:
#         opts['value'] = fd.default_value
#         opts['default'] = fd.default_value
#     elif ftype != 'message':
#         opts['value'] = None
#         opts['default'] = None
#
#     opts['name'] = fd.name
#     opts['expanded'] = False
#     return opts


from pyqtgraph import QtGui

if __name__ == '__main__':
    pg.mkQApp()
    win = QtGui.QMainWindow()
    w = LayerNode('anode')
    win.setCentralWidget(w.ui)
    win.show()
    QtGui.QApplication.instance().exec_()
    print 'here'