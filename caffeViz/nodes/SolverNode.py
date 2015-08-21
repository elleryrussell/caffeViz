__author__ = 'err258'

from caffe.proto.caffe_pb2 import SolverParameter as SolverProto
from caffeViz.customParameterTypes import LParameter
import pyqtgraph as pg
from pyqtgraph import QtCore, QtGui
from pyqtgraph.flowchart import Node
import pyqtgraph.parametertree as ptree
from caffeViz.protobufUtils import assign_proto, parsePrototxt
import caffe
import numpy as np
import os

import pyqtgraph.flowchart.library as fclib


class SolverNode(Node):
    """PsuedoNode for caffe layer"""

    generalParams = SolverProto
    nodeName = "Solver"
    sigProtoChanged = QtCore.Signal(object)
    sigOutputDataChanged = QtCore.Signal(object) # dict containing trainLoss, testLoss, and testAcc

    def __init__(self, name, proto=None, weightsFile=None, filePath=None):
        Node.__init__(self, name, allowAddInput=True, allowAddOutput=True, allowRemove=True)

        solverFD = SolverProto.DESCRIPTOR

        self.param = LParameter.create(repeated=False, fieldDescriptor=solverFD, expanded=True)
        for param in self.param.children():
            param.setToDefault()
        t = ptree.ParameterTree()
        t.addParameters(self.param, depth=1, showTop=False)
        t.setMinimumHeight(325)
        t.setVerticalScrollBarPolicy(pg.QtCore.Qt.ScrollBarAlwaysOff)
        self.ui = t
        self.proto = SolverProto()
        self.trainLoss, self.testLoss, self.testAcc = None, None, None
        self.niter, self.testInterval = None, None
        if proto is not None:
            self.setProto(proto)
        # if a filePath is given, we use it regardless of the directory of the solver prototxt, and will write a
        # temporary file in that directory for training purposes. otherwise we give the path of the solver file,
        # and hope the train file is in that directory, or else crash!
        if filePath is None:
            if proto is not None:
                filePath = os.path.dirname(proto)
            else:
                filePath = os.curdir()
        self.filePath = filePath
        self.weights = weightsFile

    def updateParamList(self, solverSpec):
        self.param.setValue(solverSpec)

    def setProto(self, proto):
        self.proto = parsePrototxt(proto, 'solver')
        self.updateParamList(self.proto)

    def updateProto(self):
        layerSpec = SolverProto()
        for param in self.param.children():
            assign_proto(layerSpec, param)
        # print layerSpec
        self.proto = layerSpec
        self.sigProtoChanged.emit(self)

    def writeProto(self, fileName=None):
        # solver file and train file must live in same directory
        if fileName is None:
            fileName = 'asolverPrototxt.prototxt'
        outFile = file(fileName, 'w')
        self.updateProto()
        outFile.write(str(self.proto))
        outFile.close()
        return fileName

    def trainNet(self):
        self.niter = self.param.child('max_iter').value()

        os.chdir(os.path.dirname(self.filePath))
        netPathParam = self.param.child('net')
        netPathParam.setValue(os.path.basename(netPathParam.value()))
        tempFileName = self.writeProto()

        solver = caffe.SGDSolver(tempFileName)

        if self.weights:
            # copy base weights for fine-tuning
            solver.net.copy_from(self.weights)

        # solve straight through -- a better approach is to define a solving loop to
        # 1. take SGD steps
        # 2. score the model by the test net `solver.test_nets[0]`
        # 3. repeat until satisfied
        # losses will also be stored in the log
        self.testInterval = self.param.child('test_interval').value()
        # this is stored as a repeated field - TODO handle multiple?
        testIterParam = self.param.child('test_iter')
        val = testIterParam.value()
        if len(val) > 0:
            self.testIter = val[0]

        # don't let caffe run the tests, we'll run them ourselves, so set test_interval to be greater than number
        # of iterations
        self.param.child('test_interval').setValue(self.niter+1)
        testIters = int(np.ceil(self.niter / self.testInterval))
        self.testAcc = np.zeros(testIters)
        self.testLoss = np.zeros(testIters)
        # output = np.zeros((self.niter, 8, 10))

        self.trainLoss = np.zeros(self.niter)
        for it in range(self.niter):
            solver.step(1)  # SGD by Caffe

            # store the train loss
            self.trainLoss[it] = solver.net.blobs['loss'].data

            # TODO cool for visualizing the change in the net's predictions - make an option?
            # # store the output on the first test batch
            # # (start the forward pass at conv1 to avoid loading new data)
            # solver.test_nets[0].forward(start='conv1')
            # output[it] = solver.test_nets[0].blobs['ip2'].data[:8]

            # run a full test every so often
            # (Caffe can also do this for us and write to a log, but we show here
            #  how to do it directly in Python, where more complicated things are easier.)
            if it % self.testInterval == 0:
                print 'Iteration', it, 'testing...'
                correct = 0
                loss = 0
                for testIt in range(self.testIter):
                    solver.test_nets[0].forward()
                    loss += solver.test_nets[0].blobs['loss'].data
                    correct += solver.test_nets[0].blobs['accuracy'].data
                    # correct += sum(solver.test_nets[0].blobs['ip2'].data.argmax(1)
                    #                == solver.test_nets[0].blobs['label'].data)
                self.testAcc[it // self.testInterval] = correct / self.testIter
                self.testLoss[it // self.testInterval] = loss / self.testIter

            self.plotTrainData(it)

        # make sure to put the value back afterward so we don't mess up the prototxt if it's saved
        self.testIterParam.setValue(self.testInterval)

    def stopTraining(self):
        pass

    def resumeTraining(self):
        pass

    def plotTrainData(self, it):
        trainLoss = self.trainLoss[0:it]
        testLoss = self.testLoss[0:it//self.testInterval]
        testAcc = self.testAcc[0:it//self.testInterval]

        # emit a signal to the plotting gods
        outputDataDict = dict(trainLoss=trainLoss, testLoss=testLoss, testAcc=testAcc)
        self.sigOutputDataChanged.emit(outputDataDict)
        pass

fclib.registerNodeType(SolverNode, [('Layers',)])

if __name__ == '__main__':
    pg.mkQApp()
    win = QtGui.QMainWindow()
    w = SolverNode('anode')
    win.setCentralWidget(w.ui)
    win.show()

    base_path = os.path.expanduser('~')
    model_dir = base_path + '/caffe/models/'

    # net_dir = 'bvlc_reference_caffenet/'
    net_dir = '91eece041c19ff8968ee/'
    dir = model_dir + net_dir
    model_path = 'train_val.prototxt'
    # weights_path = 'fcn-8s-pascalcontext.caffemodel'
    solver_path = 'solver.prototxt'

    sample_solver = dir + solver_path
    w.setProto(sample_solver)
    QtGui.QApplication.instance().exec_()
    print 'here'
