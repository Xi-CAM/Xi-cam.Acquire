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
    sigAborted = Signal()  # TODO: wireup me
    sigException = Signal()
    sigFinish = Signal()
    sigStart = Signal()

    def __init__(self, **kwargs):
        super(QRunEngine, self).__init__()

        self.RE = RunEngine(context_managers=[], **kwargs)
        self.RE.subscribe(self.sigDocumentYield.emit)

    def __call__(self, *args, **kwargs):
        print('state:', self.RE.state)
        if not self.isIdle:
            self.RE.abort()
            self.RE.reset()
            self.threadfuture.wait()

        self.threadfuture = threads.QThreadFuture(self.RE, *args, **kwargs, threadkey='RE', showBusy=True)
        self.threadfuture.start()

    @property
    def isIdle(self):
        return self.RE.state == 'idle'


    def abort(self, reason=''):
        self.RE.abort(reason=reason)



RE = QRunEngine()
RE.sigDocumentYield.connect(partial(msg.logMessage, level=msg.DEBUG))
