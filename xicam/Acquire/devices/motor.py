import logging

from ophyd.device import Component as Cpt
from ophyd.epics_motor import EpicsMotor
from ophyd.positioner import PositionerBase
from ophyd.signal import EpicsSignalRO
from ophyd.status import wait as status_wait

logger = logging.getLogger(__name__)


class DeadbandEpicsMotor(EpicsMotor):
    """EpicsMotor subclass that handles moves smaller than the motor's deadband.

    Some EPICS motor controllers don't report motion (``.MOVN`` never goes
    True, ``.DMOV`` never goes False) when the requested position is very
    close to the current position.  This causes Bluesky to wait indefinitely
    for motion completion.

    This subclass detects that condition *before* issuing the move and
    immediately marks the move as successful, while still writing the
    setpoint to the motor record for consistency.

    The tolerance for detecting a "null move" defaults to the motor record's
    retry deadband (``.RDBD``).  Set the ``move_tolerance`` class or instance
    attribute to override with a fixed value.

    Examples
    --------
    Use as a drop-in replacement for ``EpicsMotor``::

        motor = DeadbandEpicsMotor("XF:00-MOT{MC:00-Ax:00}", name="motor")

    Override the tolerance on an instance::

        motor.move_tolerance = 0.002

    Or via subclass::

        class MyMotor(DeadbandEpicsMotor):
            move_tolerance = 0.005
    """

    retry_deadband = Cpt(
        EpicsSignalRO, ".RDBD", kind="config", auto_monitor=True
    )

    # If set to a positive number, overrides retry_deadband for the
    # null-move check.  ``None`` means "use the motor record's .RDBD".
    move_tolerance = None

    def _get_move_tolerance(self):
        """Return the tolerance below which a move is considered a no-op."""
        if self.move_tolerance is not None:
            return self.move_tolerance
        try:
            rdbd = self.retry_deadband.get()
            if rdbd is not None and rdbd > 0:
                return rdbd
        except Exception:
            pass
        # Fallback when RDBD is unavailable or zero.
        return 0.001

    def move(self, position, wait=True, **kwargs):
        """Move to *position*, completing immediately if within the deadband.

        If the distance to *position* is less than or equal to the move
        tolerance (see `_get_move_tolerance`), the motor record is unlikely
        to start an actual move.  In that case the setpoint is still written
        but the returned `MoveStatus` is marked done right away so that
        Bluesky does not hang.

        All other moves are delegated to the standard `EpicsMotor.move`.
        """
        current = self.position
        tolerance = self._get_move_tolerance()

        if current is not None and abs(position - current) <= tolerance:
            logger.info(
                "%s: requested move to %s is within tolerance (%s) of "
                "current position %s; completing immediately.",
                self.name,
                position,
                tolerance,
                current,
            )
            self._started_moving = False

            # Create the MoveStatus via PositionerBase (skip EpicsMotor.move
            # so we can control when _done_moving fires).
            status = PositionerBase.move(self, position, **kwargs)

            # Still write the setpoint for bookkeeping.
            self.user_setpoint.put(position, wait=False)

            # Signal completion immediately.
            self._done_moving(success=True)

            try:
                if wait:
                    status_wait(status)
            except KeyboardInterrupt:
                self.stop()
                raise

            return status

        return super().move(position, wait=wait, **kwargs)
