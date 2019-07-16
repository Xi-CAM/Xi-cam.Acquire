from xicam.core import msg, threads
from functools import partial
from bluesky import RunEngine, Msg
import asyncio
from qtpy import QtCore
from qtpy.QtCore import QObject, Signal
from bluesky.preprocessors import subs_wrapper
import traceback


def _get_asyncio_queue(loop):
    class AsyncioQueue(asyncio.Queue):
        '''
        Asyncio queue modified for caproto server layer queue API compatibility

        NOTE: This is bound to a single event loop for compatibility with
        synchronous requests.
        '''

        def __init__(self, *, loop=loop, **kwargs):
            super().__init__(loop=loop, **kwargs)

        async def async_get(self):
            return await super().get()

        async def async_put(self, value):
            return await super().put(value)

        def get(self):
            future = asyncio.run_coroutine_threadsafe(self.async_get(), loop)
            return future.result()

        def put(self, value):
            future = asyncio.run_coroutine_threadsafe(
                self.async_put(value), loop)
            return future.result()

    return AsyncioQueue


class QRunEngine(QObject):
    sigDocumentYield = Signal(str, dict)
    sigAbort = Signal()  # TODO: wireup me
    sigException = Signal()
    sigFinish = Signal()
    sigStart = Signal()
    sigPause = Signal()
    sigResume = Signal()

    def __init__(self, **kwargs):
        super(QRunEngine, self).__init__()

        self.RE = RunEngine(context_managers=[], **kwargs)
        self.RE.subscribe(self.sigDocumentYield.emit)

    def __call__(self, *args, **kwargs):
        if not self.isIdle:
            # TODO: run confirm callback
            self.RE.abort()
            self.RE.reset()
            self.threadfuture.wait()

        self.threadfuture = threads.QThreadFuture(self.RE, *args, **kwargs,
                                                  threadkey='RE',
                                                  showBusy=True,
                                                  finished_slot=self.sigFinish.emit)
        self.threadfuture.start()
        self.sigStart.emit()

    # state_hook

    @property
    def isIdle(self):
        return self.RE.state == 'idle'

    def abort(self, reason=''):
        if self.RE.state != 'idle':
            self.RE.abort(reason=reason)
            self.sigAbort.emit()

    def pause(self, defer=False):
        if self.RE.state != 'paused':
            self.RE.request_pause(defer)
            self.sigPause.emit()

    def resume(self, ):
        if self.RE.state == 'paused':
            self.threadfuture = threads.QThreadFuture(self.RE.resume,
                                                      threadkey='RE',
                                                      showBusy=True,
                                                      finished_slot=self.sigFinish.emit)
            self.threadfuture.start()
            self.sigResume.emit()




RE = QRunEngine()
RE.sigDocumentYield.connect(partial(msg.logMessage, level=msg.DEBUG))
