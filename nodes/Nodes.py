__author__ = 'ellery'

import caffe

#### NEVERMIND!!!
# let caffe net handle prototxts to save a bunch of message passing code - just make nodes from python layers and update
# net.
# this at least has the advantage of always tying the net to the node model - you'll be able to see net statistics in
# in real time, for example.
# will cause crashes for excessive memory allocations though.

import caffe
from caffe.proto import caffe_pb2
from google.protobuf import text_format
# from caffe import layers as L, params as P, to_proto
from caffe.net_spec import _param_names


from pyqtgraph.flowchart import Flowchart, Node
import pyqtgraph.flowchart.library as fclib
from pyqtgraph.flowchart.library.common import CtrlNode
import pyqtgraph.parametertree as ptree
# from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
# import numpy as np

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
    netPB = _readProtoNetFile(filename)
    for layer in netPB.layer:
        fieldPairs = layer.ListFields()
        fields = {fd[0].name: fd[1] for fd in fieldPairs}
        for key, value in fields.items():
            if key is _param_names[str(layer.type)]+'_param':
                pFieldPairs = value.ListFields()
                fields = {fd[0].name: fd[1] for fd in pFieldPairs}
        pName = _param_names[str(layer.type)]+'_param'
        specificTypeParams = getattr(layer, pName)

## We will define an unsharp masking filter node as a subclass of CtrlNode.
## CtrlNode is just a convenience class that automatically creates its
## control widget based on a simple data structure.

class LayerNode(CtrlNode):
    """Return the input data passed through pg.gaussianFilter."""

    generalParams = caffe_pb2.LayerParameter
    associatedParams = caffe_pb2.ConvolutionParameter
    uiTemplate = [('bunny', 'spin', {'value': 1, 'step': 1, 'range': [0, None]})]
    nodeName = "UnsharpMask"

    def __init__(self, name):
        ## Define the input / output terminals available on this node
        terminals = {
            'dataIn': dict(io='in'),    # each terminal needs at least a name and
            'dataOut': dict(io='out'),  # to specify whether it is input or output
        }                              # other more advanced options are available
                                       # as well..
        CtrlNode.__init__(self, name, terminals=terminals)
        self.uiTemplate = self.makeUITemplate()
        # self.ui, self.stateGroup, self.ctrls = generateUi(self.uiTemplate)
        param = ptree.Parameter.create(name='top', type='group', children=self.uiTemplate)
        t = ptree.ParameterTree()
        t.setParameters(param, showTop=False)
        self.ui = t

    def process(self, dataIn, display=True):
        # CtrlNode has created self.ctrls, which is a dict containing {ctrlName: widget}
        sigma = self.ctrls['sigma'].value()
        strength = self.ctrls['strength'].value()
        output = dataIn - (strength * pg.gaussianFilter(dataIn, (sigma,sigma)))
        return {'dataOut': output}

    def makeUITemplate(self):
        generalFieldDescriptors = [field for field in self.generalParams().DESCRIPTOR.fields if '_param' not in field.name]
        specificFieldDescriptor = self.generalParams().DESCRIPTOR.fields_by_name['convolution_param']
        fieldDescriptors = generalFieldDescriptors+[specificFieldDescriptor]
        return [makeParamList(fd) for fd in fieldDescriptors]

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

def makeParamList(fd):
    # name = fd.name
    ftype = typeDict[fd.cpp_type]

    if ftype == 'enum':
        opts = {'type': 'list', 'values': [value.name for value in fd.enum_type.values]}
    elif ftype == 'message':
        opts = {'type': 'group', 'children': [makeParamList(mfield) for mfield in fd.message_type.fields]}
    else:
        opts = {'type': ftype}
        if fd.has_default_value:
            opts['value']= fd.default_value

    opts['name'] = fd.name
    return opts


from pyqtgraph.WidgetGroup import WidgetGroup
from pyqtgraph.widgets.ColorButton import ColorButton
from pyqtgraph import QtGui
from pyqtgraph.widgets.SpinBox import SpinBox

def generateUi(opts):
    """Convenience function for generating common UI types"""
    widget = QtGui.QWidget()
    l = QtGui.QFormLayout()
    l.setSpacing(0)
    widget.setLayout(l)
    ctrls = {}
    row = 0
    for opt in opts:
        if len(opt) == 2:
            k, t = opt
            o = {}
        elif len(opt) == 3:
            k, t, o = opt
        else:
            raise Exception("Widget specification must be (name, type) or (name, type, {opts})")
        if t == 'intSpin':
            w = QtGui.QSpinBox()
            if 'max' in o:
                w.setMaximum(o['max'])
            if 'min' in o:
                w.setMinimum(o['min'])
            if 'value' in o:
                w.setValue(o['value'])
        elif t == 'doubleSpin':
            w = QtGui.QDoubleSpinBox()
            if 'max' in o:
                w.setMaximum(o['max'])
            if 'min' in o:
                w.setMinimum(o['min'])
            if 'value' in o:
                w.setValue(o['value'])
        elif t == 'spin':
            w = SpinBox()
            w.setOpts(**o)
        elif t == 'check':
            w = QtGui.QCheckBox()
            if 'checked' in o:
                w.setChecked(o['checked'])
        elif t == 'combo':
            w = QtGui.QComboBox()
            for i in o['values']:
                w.addItem(i)
        #elif t == 'colormap':
            #w = ColorMapper()
        elif t == 'color':
            w = ColorButton()
        elif t == 'group':
            w, temp, temp = generateUi([o_ for o_ in o['mfields']])
        else:
            raise Exception("Unknown widget type '%s'" % str(t))
        if 'tip' in o:
            w.setToolTip(o['tip'])
        w.setObjectName(k)
        l.addRow(k, w)
        if o.get('hidden', False):
            w.hide()
            label = l.labelForField(w)
            label.hide()

        ctrls[k] = w
        w.rowNum = row
        row += 1
    group = WidgetGroup(widget)
    return widget, group, ctrls

if __name__ == '__main__':
    pg.mkQApp()
    win = QtGui.QMainWindow()
    w = LayerNode('anode')
    win.setCentralWidget(w.ui)
    win.show()
    QtGui.QApplication.instance().exec_()
    print 'here'