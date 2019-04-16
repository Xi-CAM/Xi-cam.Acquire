from xicam.core import msg, threads
from functools import partial
from bluesky import RunEngine, Msg
import asyncio
from qtpy import QtCore
from bluesky.preprocessors import subs_wrapper


class Teleporter(QtCore.QObject):
    name_doc = QtCore.Signal(str, dict)


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


def spawn_RE(*, loop=None, **kwargs):
    RE = RunEngine(context_managers=[], **kwargs)
    queue = _get_asyncio_queue(RE.loop)()
    t = Teleporter()

    async def get_next_message(msg):
        return await queue.async_get()

    RE.register_command('next_plan', get_next_message)

    def forever_plan():
        while True:
            plan = yield Msg('next_plan')
            try:
                yield from plan
            except GeneratorExit:
                raise
            except Exception as ex:
                print(f'things went sideways \n{ex}')

    def thread_task():
        RE(forever_plan())

    threadfuture = threads.QThreadFuture(method=thread_task,
                                         threadkey='RE',
                                         showBusy=False)
    RE.subscribe(t.name_doc.emit)
    threadfuture.start()

    return RE, queue, threadfuture, t


def queue_and_sub(plan, sub):
    queue.put(subs_wrapper(plan, partial(threads.invoke_in_main_thread, sub)))


RE, queue, thread, teleporter = spawn_RE(md={'location': 'server'})
# bec = BestEffortCallback()
# bec.disable_plots()
# RE.subscribe(bec)

teleporter.name_doc.connect(partial(msg.logMessage, level=msg.DEBUG))
