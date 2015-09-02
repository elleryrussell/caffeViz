__author__ = 'err258'

import os

from caffe.proto.caffe_pb2 import SolverParameter as SolverProto
import pyqtgraph as pg
from pyqtgraph import QtCore, QtGui
from pyqtgraph.flowchart import Node
import pyqtgraph.parametertree as ptree
import numpy as np
import pyqtgraph.flowchart.library as fclib

from caffeViz.customParameterTypes import LParameter
from caffeViz.protobufUtils import assign_proto, parsePrototxt


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
        niter = self.param.child('max_iter').value()
        mode = self.param.child('solver_mode').value()
        testInterval = self.param.child('test_interval').value()
        # don't let caffe run the tests, we'll run them ourselves, so set test_interval to be greater than number
        # of iterations
        self.param.child('test_interval').setValue(niter + 1)
        testIterParam = self.param.child('test_iter')
        # stored as a repeated field
        val = testIterParam.value()
        if len(val) > 0:
            testIter = val[0]
        else:
            testIter = 0

        # don't let caffe run the tests, we'll run them ourselves, so set test_interval to be greater than number
        # of iterations
        testIters = int(np.ceil(niter / testInterval))

        os.chdir(os.path.dirname(self.filePath))
        netPathParam = self.param.child('net')
        netPathParam.setValue(os.path.basename(netPathParam.value()))
        tempFileName = self.writeProto()

        self.testIterParam.setValue(self.testInterval)
        
        solver = RemoteSolver(tempFileName, niter, testInterval, testIter, self.weights, mode)

        # when we get a response, we plot it
        self.trainLoss = {outputName: np.zeros(niter) for outputName in solver.trainOutputs}
        self.testLoss = {outputName: np.zeros(testIters) for outputName in solver.testLosses}
        # assume any output which is only present in the test net is an accuracy layer
        self.testAcc = {outputName: np.zeros(testIters) for outputName in solver.testAccuracies}

        self.plotTrainData(it)



    def stopTraining(self):
        pass

    def resumeTraining(self):
        pass

    def plotTrainData(self, it):
        trainLoss = {outputName: lossArr[:it] for outputName, lossArr in self.trainLoss.items()}
        testLoss = {outputName: lossArr[:it // self.testInterval] for outputName, lossArr in self.testLoss.items()}
        testAcc = {outputName: lossArr[:it // self.testInterval] for outputName, lossArr in self.testAcc.items()}

        # emit a signal to the plotting gods
        outputDataDict = dict(trainLoss=trainLoss, testLoss=testLoss, testAcc=testAcc)
        self.sigOutputDataChanged.emit(outputDataDict)

fclib.registerNodeType(SolverNode, [('Layers',)])


class RemoteSolver(object):
    def __init__(self, filename, niter, testInterval, testIter, weights=None, mode=0):
        import pyqtgraph.multiprocess as mp
        # create a remote process
        proc = mp.QtProcess()
        # import this module in remote process
        rcaffe = proc._import('caffe')

        # this solver lives in the remote process
        solver = rcaffe.SGDSolver(filename)

        if weights is not None:
            # copy base weights for fine-tuning
            solver.net.copy_from(weights)

        # solve straight through -- a better approach is to define a solving loop to
        # 1. take SGD steps
        # 2. score the model by the test net `solver.test_nets[0]`
        # 3. repeat until satisfied
        # losses will also be stored in the log
        # mode = self.param.child('solver_mode').value()
        if mode == 1:
            rcaffe.set_mode_gpu()

        trainOutputs = solver.net.outputs

        for it in range(niter):
            solver.step(1)  # SGD by Caffe
            print 'Iteration {}/{}'.format(it, niter)

            # store the train loss
            # TODO get different loss layers for both train and test mode
            trainLosses = {}
            for outputName in trainOutputs:
                trainLosses[outputName] = solver.net.blobs[outputName].data

            # TODO cool for visualizing the change in the net's predictions - make an option?
            # # store the output on the first test batch
            # # (start the forward pass at conv1 to avoid loading new data)
            # solver.test_nets[0].forward(start='conv1')
            # output[it] = solver.test_nets[0].blobs['ip2'].data[:8]

            # run a full test every so often
            # (Caffe can also do this for us and write to a log, but we show here
            #  how to do it directly in Python, where more complicated things are easier.)

            if it % testInterval == 0 and it > 0:
                print 'Iteration', it, 'testing...'
                testLosses = {}
                for outputName in trainOutputs:
                    testLosses[outputName] = 0
                accNames = [outputName for outputName in solver.test_nets[0].outputs if outputName not in trainOutputs]
                testAccuracies = {outputName: 0 for outputName in accNames}
                for testIt in range(testIter):
                    solver.test_nets[0].forward()
                    for testDict in [testLosses, testAccuracies]:
                        for lossName in testDict.keys():
                            testDict[lossName] += solver.test_nets[0].blobs[lossName].data
                # divide accuracies and losses by number of iterations
                for testDict in [testLosses, testAccuracies]:
                    for key in testDict.keys():
                        testDict[key] /= testIter

    def trainOutputs(self):
        pass

    def testLosses(self):
        pass

    def testAccuracies(self):
        pass








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
