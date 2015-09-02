__author__ = 'ellery'

import pyqtgraph as pg
from pyqtgraph import QtCore, ComboBox
from pyqtgraph.flowchart import Node
import pyqtgraph.flowchart.library as fclib
import numpy as np

from caffeViz.utils import split_every


class ImagePlotNode(Node):
    """
    Node that simultaneously plots an image and different types of plots.
    Can pass in curves, points, and rois in addition to images
    """

    nodeName = 'ImagePlot'
    sigViewChanged = QtCore.Signal(object)

    def __init__(self, name, **kwargs):
        self.plot = None
        self.plots = {}  # list of available plots user may select from
        self.ui = None
        self.imageItem = None
        self.plotItem = None
        self.scatterDefaults = dict(symbol='+', symbolPen='r', symbolSize=8, symbolBrush='r', pen=None)
        self.curveDefaults = dict(pen='w')

        opts = dict(allowAddInput=True,
                       terminals=dict(image={'io': 'in'}, points={'io': 'in'}, curves={'io': 'in'}, rois={'io': 'in'}))
        opts.update(**kwargs)

        ## Initialize node with only a single input terminal
        Node.__init__(self, name, **opts)

    def setPlot(self, plot):  ## setView must be called by the program
        if plot == self.plot:
            return
        self.plot = plot
        self.plotItem = self.plot.plotItem
        self.plotItem.setAspectLocked()
        self.plotItem.invertY(True)
        # self.plot.plotItem.addItem(self.plotItem)
        # clear data from previous plot
        self.updateUi()
        self.update()
        self.sigViewChanged.emit(self)

    def process(self, image=None, points=None, curves=None, rois=None, display=True, **additionalPlots):
        self.plotItem.clear()
        defaults = dict(symbol='+', symbolPen='r', symbolSize=8, symbolBrush='r', pen=None)
        if display and self.plot is not None:
            if image is not None:
                self.plotImage(image)

            if points is not None:
                self.plotPoints(points)

            for name, additionalPlot in additionalPlots.items():
                if additionalPlot is not None:
                    for childItem in self.plotItem.items:
                        if isinstance(childItem, pg.PlotDataItem):
                            if childItem.name() == name:
                                childItem.clear()
                defaults.update(symbolPen='b')
                self.plotItem.plot(x=additionalPlot[:, 1], y=additionalPlot[:, 0], name=name, **defaults)

        if rois is not None:
            for roi in rois:
                plotROI = pg.ROI(roi.r0[::-1], roi.size[::-1])
                self.plotItem.addItem(plotROI)

    def plotImage(self, image):
        # sort out of image is a blob from caffenetOutputs[blobName]
        # if the image is 3D and the trailing dimension is not 3 or 4 (RGB(A)), it's a blob
        if image.ndim == 4:
            # TODO handle batched input
            # for now, just take a 3D blob: ch x h x w
            image = np.squeeze(image)
            if image.ndim == 3:
                if any([image.shape[0] == i for i in [3, 4]]):
                    # BGR - RGB
                    image = image[::-1]
                    # to h x w x ch
                    image = np.rollaxis(image, 0, 3)
                else:
                    image = self.constructImageFromBlob(blob=image)
        # pyqtgraph expects w x h..
        imageItem = pg.ImageItem(image.swapaxes(0, 1))
        self.plotItem.addItem(imageItem)

    def plotPoints(self, points, **plotArgs):
        defaults = self.scatterDefaults.copy()
        defaults.update(**plotArgs)
        self.plotItem.plot(x=points[:, 1], y=points[:, 0], **defaults)

    def plotCurves(self, curves, **plotArgs):
        defaults = self.curveDefaults.copy()
        defaults.update(**plotArgs)
        for curve in curves:
            self.plotItem.plot(curve, **defaults)

    def constructImageFromBlob(self, blob):
        imShape = np.array(blob.shape[1:])
        # pad by the smaller of the largest image dimension/10 or 3
        pad = min(np.max(imShape)/10, 3)
        blob = np.pad(blob, pad_width=((0, 0), (0, pad), (0, pad)), mode='constant')

        # make a squarish grid of the layers in the blob
        numChannels = blob.shape[0]
        minWidth = np.floor(np.sqrt(numChannels))

        aList = []

        # cols grow to accomodate demand first, then rows
        numCols = int(np.ceil(numChannels/minWidth))
        # numRows = int(np.ceil(numChannels/numCols))

        # take a stack of minWidth channels (like dealing cards one person at a time)
        splits = split_every(numCols, blob)
        for split in splits:
            aList.append(np.hstack(split))
            # aList.append(np.hstack(blob[i * numCols:(i + 1) * numCols]))
        aList[-1] = aList[-1].T.copy()
        aList[-1].resize(aList[0].shape[::-1])

        # last.resize(aList[0].shape[::-1], refCheck=False)
        # last = last.T
        # last.resize(aList[0].shape, refcheck=False)
        # aList[-1] = last
        aList[-1] = aList[-1].T
        return np.vstack(aList)[:-pad, :-pad]
        #
        # imShape = np.array(blob.shape[1:])
        # # pad by the smaller of the largest image dimension/10 or 3
        # pad = np.min(np.max(imShape)/10, 3)
        # # make a square grid of the layers in the blob
        # numChannels = blob.shape(0)
        # minWidth = np.floor(np.sqrt(numChannels))
        # boxSize = minWidth*minWidth
        # remainder = numChannels - boxSize
        # tileShape = np.array([minWidth, minWidth], dtype=int)
        # if remainder > 0:
        #     # if there are less extra elements than the size of the box, we can just add a column, otherwise add both
        #     # a row and col
        #     if boxSize < minWidth:
        #         tileShape[1] += 1
        #     else:
        #         tileShape += 1
        # blob = np.pad(blob, pad_width=((0,0),(0,pad),(0,pad)), mode='constant')






        # now make a big array to put everything into, this is image shape plus padding * num of tiles in each
        # dimension, with the padding subtracted off the last row/col
        # bigShape = (tileShape * (imShape + pad)) - pad
        # bigImage = 255 * np.zeros(bigShape)
        # yArr, xArr = np.indices(tileShape)
        # yxPairs = np.dstack((yArr.flatten(), xArr.flatten()))[0]
        # for i, yxPair in enumerate(yxPairs):
        #     start = yxPair * (imShape + pad)
        #     end = start + imShape
        #     roi = ROI(r0=start[::-1], r1=end[::-1])
        #     bigImage[roi.imSlice] = blob[i]
        # return bigImage


    def ctrlWidget(self):
        if self.ui is None:
            self.ui = ComboBox()
            self.ui.currentIndexChanged.connect(self.plotSelected)
            self.updateUi()
        return self.ui

    def plotSelected(self, index):
        self.setPlot(self.ui.value())

    def setPlotList(self, plots):
        """
        Specify the set of plots (ImageView) that the user may
        select from.

        *plots* must be a dictionary of {name: plot} pairs.
        """
        self.plots = plots
        self.updateUi()

    def updateUi(self):
        # sets list and automatically preserves previous selection
        self.ui.setItems(self.plots)
        try:
            self.ui.setValue(self.plots)
        except ValueError:
            pass

fclib.registerNodeType(ImagePlotNode, [('Display',)])