import time
from queue import PriorityQueue, Empty
from dataclasses import dataclass, field
from pymongo.errors import OperationFailure
from typing import Any, Callable

from bluesky.utils import DuringTask, RunEngineInterrupted
from xicam.core import msg, threads
from xicam.gui.utils import ParameterizedPlan, ParameterDialog
from functools import wraps, partial
import distributed  # this insulates from errors related to dask asserting its own EventLoopPolicy as squashing the event loop setup for bluesky
from bluesky import RunEngine, Msg
import asyncio
from qtpy import QtCore
from qtpy.QtCore import QObject, Signal
from bluesky.preprocessors import subs_wrapper
import traceback
import os

from xicam.Acquire.widgets.dialogs import MetadataDialog


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


@dataclass(order=True)
class PrioritizedPlan:
    priority: int
    args: Any = field(compare=False)


class QRunEngine(QObject):
    sigDocumentYield = Signal(str, dict)
    sigAbort = Signal()  # TODO: wireup me
    sigException = Signal(Exception)
    sigFinish = Signal()
    sigStart = Signal()
    sigPause = Signal()
    sigResume = Signal()
    sigReady = Signal()

    def __init__(self, **kwargs):
        super(QRunEngine, self).__init__()

        self._RE = None
        self._kwargs = kwargs

        self.sigFinish.connect(self._check_if_ready)
        self.sigAbort.connect(self._check_if_ready)
        self.sigException.connect(self._check_if_ready)

        self.queue = PriorityQueue()
        self.process_queue()

        self.kwargs_callables = set()

    @property
    def RE(self):
        return self._RE

    def _close_RE(self):
        if self._RE.state != 'idle':
            self._RE.abort('Application is closing.')

    @threads.method(threadkey="run_engine", showBusy=False)
    def process_queue(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self._RE = RunEngine(context_managers=[], during_task=DuringTask(), loop=self.loop, **self._kwargs)
        self._RE.subscribe(self.sigDocumentYield.emit)
        self._RE.subscribe(self._stop_check, 'stop')

        # TODO: pull from settings plugin
        from suitcase.mongo_normalized import Serializer
        # TODO create single databroker db
        # python-dotenv stores name-value pairs in .env (add to .gitginore)
        username = os.getenv("USER_MONGO")
        pw = os.getenv("PASSWD_MONGO")
        try:
            self.RE.subscribe(Serializer(f"mongodb://{username}:{pw}@localhost:27017/mds?authsource=mds",
                                         f"mongodb://{username}:{pw}@localhost:27017/fs?authsource=fs"))
        except OperationFailure as err:
            msg.notifyMessage("Could not connect to local mongo database.",
                              title="xicam.Acquire Error",
                              level=msg.ERROR)
            msg.logError(err)

        while True:
            try:
                priority_plan = self.queue.get(block=True, timeout=.1)  # timeout is arbitrary, we'll come right back
            except Empty:
                continue
            priority, (args, kwargs) = priority_plan.priority, priority_plan.args

            self.sigStart.emit()
            msg.showBusy()
            try:
                self.RE(*args, **kwargs)
            except RunEngineInterrupted:
                msg.showMessage("Run has been aborted by the user.")
            except Exception as ex:
                msg.notifyMessage(f"An error occured during a Bluesky plan: {ex}")
                msg.logError(ex)
                self.sigException.emit(ex)
            finally:
                msg.showReady()
            self.queue.task_done()
            self.sigFinish.emit()

    @wraps(RunEngine.__call__)
    def __call__(self, *args, **kwargs):
        self.put(*args, **kwargs)

    @property
    def isIdle(self):
        return self.RE.state == 'idle'

    def abort(self, reason=''):
        if self.RE.state == 'running':
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

    def put(self, *args, priority=1, suppress_parameters_dialog=False, **kwargs):
        # handle ParameterizedPlan's
        plan = args[0]
        if hasattr(plan, 'parameter') and not suppress_parameters_dialog:
            # Ask for parameters
            param = plan.parameter
            if param:
                ParameterDialog(param).exec_()

        reserved = set(kwargs.keys()).union(['plan_type', 'plan_args', 'scan_id', 'time', 'uid'])
        self._metadata_dialog = MetadataDialog(reserved=reserved)
        self._metadata_dialog.open()
        self._metadata_dialog.accepted.connect(partial(self._put, self._metadata_dialog, priority, args, kwargs))

    def _put(self, dialog: MetadataDialog, priority, args, kwargs):
        metadata = dialog.get_metadata()
        kwargs.update(metadata)
        for kwargs_callable in self.kwargs_callables:
            kwargs.update(kwargs_callable())
        self.queue.put(PrioritizedPlan(priority, (args, kwargs)))

    def _check_if_ready(self):
        # RE has finished processing everything in the queue
        if self.RE.state == 'idle' and self.queue.unfinished_tasks == 0:
            self.sigReady.emit()

    def subscribe_kwargs_callable(self, kwargs_callable:Callable):
        self.kwargs_callables.add(kwargs_callable)

    def unsubscribe_kwargs_callable(self, kwargs_callable:Callable):
        self.kwargs_callables.remove(kwargs_callable)

    def _stop_check(self, name, doc):
        reason = doc.get('reason', None)
        if reason:
            msg.notifyMessage(f'Run failed (see log): {reason}')


RE = None


def initialize():
    global RE


def get_run_engine():
    global RE
    if RE is None:
        RE = QRunEngine()
        RE.sigDocumentYield.connect(partial(msg.logMessage, level=msg.DEBUG))
    return RE
