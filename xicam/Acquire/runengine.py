import time
from queue import PriorityQueue, Empty
from dataclasses import dataclass, field
from pymongo.errors import OperationFailure
from typing import Any

from bluesky.utils import DuringTask, RunEngineInterrupted
from xicam.core import msg, threads
from xicam.gui.utils import ParameterizedPlan, ParameterDialog
from functools import wraps, partial
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

        self.RE = RunEngine(context_managers=[], during_task=DuringTask(), **kwargs)
        self.RE.subscribe(self.sigDocumentYield.emit)

        # TODO: pull from settings plugin
        from suitcase.mongo_normalized import Serializer
        #TODO create single databroker db
        #python-dotenv stores name-value pairs in .env (add to .gitginore)
        username=os.getenv("USER_MONGO")
        pw = os.getenv("PASSWD_MONGO")
        try:
            self.RE.subscribe(Serializer(f"mongodb://{username}:{pw}@localhost:27017/mds?authsource=mds",
                                         f"mongodb://{username}:{pw}@localhost:27017/fs?authsource=fs"))
        except OperationFailure as err:
            msg.notifyMessage("Could not connect to local mongo database.",
                              title="xicam.Acquire Error",
                              level=msg.ERROR)
            msg.logError(err)

        self.sigFinish.connect(self._check_if_ready)

        self.queue = PriorityQueue()
        self.process_queue()

    @threads.method(threadkey="run_engine", showBusy=False)
    def process_queue(self):
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

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
                msg.showMessage("An error occured during a Bluesky plan. See the Xi-CAM log for details.")
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

    def put(self, *args, priority=1, **kwargs):
        # handle ParameterizedPlan's
        plan = args[0]
        if hasattr(args[0], 'parameter'):
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
        self.queue.put(PrioritizedPlan(priority, (args, kwargs)))

    def _check_if_ready(self):
        # RE has finished processing everything in the queue
        if self.RE.state == 'idle' and self.queue.unfinished_tasks == 0:
            self.sigReady.emit()


RE = None


def initialize():
    global RE


def get_run_engine():
    global RE
    if RE is None:
        RE = QRunEngine()
        RE.sigDocumentYield.connect(partial(msg.logMessage, level=msg.DEBUG))
    return RE
