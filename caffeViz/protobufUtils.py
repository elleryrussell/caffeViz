from caffe.proto.caffe_pb2 import NetParameter as NetProto, SolverParameter as SolverProto
from google.protobuf import text_format

__author__ = 'err258'


def assign_proto(proto, param):
    """Assign a Parameter to a protobuf message, based on the Parameter type (in recursive fashion)"""

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


def _readProtoNetFile(filepath):
    net_config = NetProto()

    return _readProtoFile(filepath, net_config)


def _readProtoSolverFile(filepath):
    solver_config = SolverProto()

    return _readProtoFile(filepath, solver_config)


def _readProtoFile(filepath, parser_object):
    file = open(filepath, "r")

    if not file:
        raise NameError("ERROR (" + filepath + ")!")

    text_format.Merge(str(file.read()), parser_object)
    file.close()
    return parser_object


def parsePrototxt(filename, typ):
    """return a list of layers and their (perhaps nested) fields to initialize Nodes
    :param typ: a string indicating the Protobuf type, can be 'net' or 'solver'
    """
    if typ == 'net':
        proto = _readProtoNetFile(filename)
        # all of the layer messages
    elif typ == 'solver':
        proto = _readProtoSolverFile(filename)
    else:
        raise ValueError('not a supported protobuf type')

    return proto