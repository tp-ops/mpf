"""Baseclass for ball device ejectors."""

MYPY = False
if MYPY:    # pragma: no cover
    from mpf.core.machine import MachineController  # pylint: disable-msg=cyclic-import,unused-import
    from mpf.devices.ball_device.ball_device import BallDevice  # pylint: disable-msg=cyclic-import,unused-import


class BallDeviceEjector:

    """Ejector for a ball device.

    It has to implement at least one of eject_one_ball or eject_all_balls.
    """

    __slots__ = ["config", "ball_device", "machine"]

    def __init__(self, config: dict, ball_device: "BallDevice", machine: "MachineController") -> None:
        """initialize ejector."""
        self.config = config
        self.ball_device = ball_device
        self.machine = machine

    async def eject_one_ball(self, is_jammed, eject_try, balls_in_device):
        """Eject one ball."""
        raise NotImplementedError()

    async def reorder_balls(self):
        """Reorder balls without ejecting.

        This might be useful when count become unstable during a jam condition.
        """
        raise NotImplementedError()

    def ball_search(self, phase, iteration):
        """Search ball in device."""
        raise NotImplementedError()

    def debug_log(self, *args, **kwargs):
        """Debug log."""
        self.ball_device.debug_log(*args, **kwargs)

    def info_log(self, *args, **kwargs):
        """Info log."""
        self.ball_device.info_log(*args, **kwargs)

    def warning_log(self, *args, **kwargs):
        """Warning log."""
        self.ball_device.warning_log(*args, **kwargs)
