from collections import OrderedDict

from pyqtgraph.parametertree.Parameter import Parameter, PARAM_TYPES
from pyqtgraph.parametertree.parameterTypes import GroupParameter, registerParameterType, SimpleParameter, ListParameter

__author__ = 'ellery'


class LParameter(Parameter):
    def create(**opts):
        fd = opts.get('fieldDescriptor', None)
        if fd is None:
            cls = Parameter
        else:
            typ = typeDict[fd.cpp_type]
            label = fd.label
            if label == 3:
                cls = PARAM_TYPES['repeated']
            else:
                cls = PARAM_TYPES[opts[typ]]
        return cls(**opts)

    def __init__(self, fieldDescriptor=None, **opts):
        assert fieldDescriptor is not None
        self.fieldDescriptor = fieldDescriptor

        name = fieldDescriptor.name
        default = fieldDescriptor.default_value
        expanded = False

        Parameter.__init__(self, name=name, default=default, expanded=expanded, **opts)


class LRepeatedParameter(GroupParameter, LParameter):
    def __init__(self, **kwargs):
        GroupParameter.__init__(self, addText='add', **kwargs)

    def addNew(self, value=None, default=None):
        name = self.name() + str(len(self.childs) + 1)
        child = LParameter.create(name=name, fieldDescriptor=self.fieldDescriptor, value=value, default=default,
                                      removable=True, renamable=True)

        return self.addChild(child=child)

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


registerParameterType('repeated', LRepeatedParameter)


class LMessageParameter(GroupParameter, LParameter):
    def __init__(self, value=None, fieldDescriptor=None, **kwargs):
        self.message_type = self.fieldDescriptor.message_type
        children = [LParameter.create(fieldDescriptor=mfield) for mfield in self.message_type.fields
                    if '_param' not in mfield.name]

        GroupParameter.__init__(self, children=children, **kwargs)
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

        # def setValue(self, value, blockSignal=None):
        #     for child in self.children():
        #         child.setValue(value.name.value)


registerParameterType('message', LMessageParameter)


class LDefaultParam(SimpleParameter, LParameter):
    def __init__(self, value=None, default=None, *args, **kwargs):
        SimpleParameter.__init__(self, value=value, default=default, *args, **kwargs)
        self.setDefault(default)
        self.setValue(value)


registerParameterType('int', LDefaultParam, override=True)
registerParameterType('float', LDefaultParam, override=True)
registerParameterType('str', LDefaultParam, override=True)


class enumParameter(ListParameter):
    def __init__(self, **opts):
        assert 'fieldDescriptor' in opts.keys()
        fd = opts['fieldDescriptor']

        limits = OrderedDict()
        if not fd.has_default_value:
            limits['None'] = None
        for value in fd.enum_type.values:
            limits[value.name] = value.number
        opts['limits'] = limits

        opts['default'] = fd.default_value

        ListParameter.__init__(self, **opts)


registerParameterType('enum', enumParameter)

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
#     # repeated field container
#     elif fd.label == 3:
#         opts = {'type': 'repeated', 'addText': 'add', 'field': fd, 'subTyp':ftype}
#         # if ftype == 'message':
#             # subParamList = [makeParamList(mfield) for mfield in fd.message_type.fields]
#             # opts['subParamList'] = subParamList
#     elif ftype == 'message':
#         opts = {'type': 'group', 'children': [makeParamList(mfield) for mfield in fd.message_type.fields]}
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
