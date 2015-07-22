__author__ = 'err258'


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