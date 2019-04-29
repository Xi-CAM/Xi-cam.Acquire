from xicam.core import msg, threads
from functools import partial
from bluesky import RunEngine, Msg
import asyncio
from qtpy import QtCore
from qtpy.QtCore import QObject, Signal
from bluesky.preprocessors import subs_wrapper


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
        self.queue = _get_asyncio_queue(self.RE.loop)()
        self.is_running = False

        self.RE.register_command('next_plan', self._get_next_message)

        self.threadfuture = threads.QThreadFuture(method=self._thread_task,
                                                  threadkey='RE',
                                                  showBusy=False)
        self.RE.subscribe(self.sigDocumentYield.emit)
        self.threadfuture.start()

    def _thread_task(self):
        self.RE(self._forever_plan())

    def _forever_plan(self):
        while True:
            plan = yield Msg('next_plan')
            self.is_running = True
            self.sigStart.emit()
            try:
                yield from plan
            except GeneratorExit:
                raise
            except Exception as ex:
                msg.showMessage('Exception in RunEngine:', level=msg.ERROR)
                msg.logError(ex)
            finally:
                self.sigFinish.emit()
                self.is_running = False

    async def _get_next_message(self, msg):
        return await self.queue.async_get()

    def abort(self, reason=''):
        self.RE.abort(reason=reason)

    def put(self, plan, sub=None):
        if sub:
            plan = subs_wrapper(plan, partial(threads.invoke_in_main_thread, sub))
        self.queue.put(plan)


RE = QRunEngine()
RE.sigDocumentYield.connect(partial(msg.logMessage, level=msg.DEBUG))
