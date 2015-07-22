from collections import OrderedDict
from google.protobuf.descriptor_pb2 import FieldDescriptorProto
from google.protobuf.message import Message

from pyqtgraph import QtCore

from pyqtgraph.parametertree.Parameter import Parameter
from pyqtgraph.parametertree.parameterTypes import GroupParameter, SimpleParameter, ListParameter

__author__ = 'ellery'

LPARAM_TYPES = {}
LPARAM_NAMES = {}

def registerLParameterType(name, cls, override=False):
    global LPARAM_TYPES
    if name in LPARAM_TYPES and not override:
        raise Exception("Parameter type '%s' already exists (use override=True to replace)" % name)
    LPARAM_TYPES[name] = cls
    LPARAM_NAMES[cls] = name


class LParameter(Parameter):

    @staticmethod
    def create(**opts):
        fd = opts.get('fieldDescriptor', None)
        if fd is None:
            cls = Parameter
        else:
            typ = typeDict[fd.cpp_type]
            label = fd.label
            if label == 3 and opts.get('repeated', True) is True:
                cls = LPARAM_TYPES['repeated']
            else:
                cls = LPARAM_TYPES[typ]
        return cls(**opts)

    def __init__(self, fieldDescriptor=None, **opts):
        assert fieldDescriptor is not None
        self.fieldDescriptor = fieldDescriptor

        type = typeDict[fieldDescriptor.cpp_type]
        if 'name' not in opts.keys():
            opts['name'] = fieldDescriptor.name
        default = fieldDescriptor.default_value
        if 'expanded' not in opts.keys():
            opts['expanded'] = False

        Parameter.__init__(self, default=default, type=type, **opts)

    # def protoValue(self):
    #     if not self.valueIsDefault():
    #         protoMessage = self.fieldDescriptor.name


class LRepeatedParameter(GroupParameter, LParameter):
    # sigChildAdded = QtCore.Signal(object, object) # self, child

    def __init__(self, **kwargs):
        LParameter.__init__(self, **kwargs)
        GroupParameter.__init__(self, addText='add', **self.opts)
        self.opts['type'] = 'repeated'

    def addNew(self, value=None):
        name = self.name() + str(len(self.childs) + 1)
        fd = self.fieldDescriptor
        child = LParameter.create(name=name, repeated=False, fieldDescriptor=fd, value=value,
                                      removable=True, renamable=True)

        # self.sigChildAdded.emit(self, child, pos)
        return self.addChild(child=child)

    def setValue(self, value, blockSignal=None, clear=False):
        if clear:
            self.clearChildren()
        for spec in value:
            child = self.addNew()
            child.setValue(spec)

    def valueIsDefault(self):
        """if child has any children always return True"""
        if len(self.children()) > 0:
            return False
        else:
            return True
            # for child in self.children():
            #     if not child.valueIsDefault():
            #         return False
            # return True

    def setToDefault(self):
        for child in self.children():
            child.setToDefault()

    def value(self):
        return [child.value() for child in self.children()]

    def protoValue(self):
        for val in self.value():
            pass


registerLParameterType('repeated', LRepeatedParameter)


class LMessageParameter(GroupParameter, LParameter):
    def __init__(self, value=None, **kwargs):
        LParameter.__init__(self, **kwargs)
        self.message_type = self.fieldDescriptor.message_type
        children = [LParameter.create(fieldDescriptor=mfield) for mfield in self.message_type.fields
                    if '_param' not in mfield.name]

        GroupParameter.__init__(self, children=children, **self.opts)
        # if self.value() is not None:
        #     paramsList = makeParamList(self.value())
        #     self.addChild(paramsList)

    def valueIsDefault(self):
        for child in self.children():
            if not child.valueIsDefault():
                return False
        return True

    def setToDefault(self):
        for child in self.children():
            child.setToDefault()

    def value(self):
        childList = [(child.name(), child.value()) for child in self.children() if not child.valueIsDefault()]
        return childList

    def setValue(self, value, blockSignal=None):
        spec = value
        for field, value in spec.ListFields():
            self.child(field.name).setValue(value)
            # pass

    def proto(self):
        fd = self.fieldDescriptor
        assert isinstance(fd, FieldDescriptorProto)

        # def setValue(self, value, blockSignal=None):
        #     for child in self.children():
        #         child.setValue(value.name.value)


registerLParameterType('message', LMessageParameter)


class LDefaultParam(SimpleParameter, LParameter):
    def __init__(self, *args, **kwargs):
        LParameter.__init__(self, *args, **kwargs)
        SimpleParameter.__init__(self, *args, **self.opts)
        # self.setDefault(default)
        # self.setValue(value)


registerLParameterType('int', LDefaultParam, override=True)
registerLParameterType('float', LDefaultParam, override=True)
registerLParameterType('str', LDefaultParam, override=True)
registerLParameterType('bool', LDefaultParam, override=True)


class enumParameter(ListParameter, LParameter):
    def __init__(self, **opts):
        LParameter.__init__(self, **opts)
        opts = self.opts
        fd = self.fieldDescriptor

        limits = OrderedDict()
        if not fd.has_default_value:
            limits['None'] = -1
            opts['default'] = -1
        else:
            opts['default'] = fd.default_value
        for value in fd.enum_type.values:
            limits[value.name] = value.number
        opts['limits'] = limits



        ListParameter.__init__(self, **opts)

    def setValue(self, value, blockSignal=None):
        if isinstance(value, Message):
            val = value.number
        else:
            val = value
        ListParameter.setValue(self, val)


registerLParameterType('enum', enumParameter)

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


