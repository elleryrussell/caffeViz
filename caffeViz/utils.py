__author__ = 'ellery'

import numpy as np
from itertools import islice


from contextlib import contextmanager

@contextmanager
def slotDisconnected(signal, slot):
    """
    Create context to perform operations with given slot disconnected from
    given signal and automatically connected afterwards.

    usage:
        with slot_disconnected(chkbox.stateChanged, self._stateChanged):
            foo()
            bar()
    """

    signal.disconnect(slot)
    yield
    signal.connect(slot)

@contextmanager
def signalsBlocked(qObject):
    """
    Create context to perform operations with given signal blocked and
    automatically connected afterwards.

    usage:
        with signalsBlocked(chkbox.stateChanged):
            foo()
            bar()
    """

    qObject.blockSignals(True)
    yield
    qObject.blockSignals(False)

def split_every(n, iterable):
    """
    split an iterable into batches
    :param n: number per split
    :param iterable: iterable to split
    :return: a generator that returns tuples such as (1,2,3), (4,5,6) ...
    """
    i = iter(iterable)
    piece = list(islice(i, n))
    while piece:
        yield piece
        piece = list(islice(i, n))

class ROI(object):
    def __init__(self, r0=None, r1=None, rc=None, roi_radius=None):
        if r0 is not None and r1 is not None:
            self._roi = np.array([r0, r1], dtype=np.long)
            self._rc = (self.r1-self.r0)/2.
        elif rc is not None and roi_radius is not None:
            self._roi = np.array([rc-roi_radius, rc+roi_radius], dtype=np.long)
            self._rc = rc
        else:
            raise ValueError('ROI takes either both r0 and r1 or both rc and roi_range')

    @property
    def r0(self):
        return self._roi[0]

    @property
    def r1(self):
        return self._roi[1]

    @property
    def imSlice(self):
        """(y0:y1, x0:x1)"""
        t = self._roi.T
        return slice(*t[1]), slice(*t[0])

    @property
    def size(self):
        """actual center of roi (in ROI's own coords)"""
        return self.r1 - self.r0

    @property
    def center(self):
        """actual center of roi (in ROI's own coords)"""
        return self.size/2

    @property
    def rc(self):
        """original center before clipping(in ROI's own coords)"""
        return self._rc

    @property
    def list(self):
        """[x0, x1, y0, y1]"""
        return self._roi.T.flatten()

    def clip(self, a_max, a_min=0):
        self._roi = np.clip(self._roi, a_min=0, a_max=a_max)

    def scale(self, roiScale):
        origin = self.center + self.r0
        return ROI(r0=(origin - self.center*roiScale), r1=(origin + self.center*roiScale))

    def __str__(self):
        return 'x: {}-{}, y: {}-{}'.format(*self.list)