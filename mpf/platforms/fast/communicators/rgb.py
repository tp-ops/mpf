from packaging import version

from mpf.core.utility_functions import Util
from mpf.platforms.fast.communicators.base import FastSerialCommunicator

MIN_FW = version.parse('0.87') # override in subclass

class FastRgbCommunicator(FastSerialCommunicator):

    """Handles the serial communication for legacy FAST RGB processors including
    the Nano Controller and FP-EXP-0800 LED controller."""

    ignored_messages = ['RA:P',
                        'RF:',
                        'RS:P']

    def __init__(self, platform, processor, config):
        super().__init__(platform, processor, config)

        self._led_task = None
        self.message_processors['!B:'] = self._process_boot_msg

    def _process_boot_msg(self, msg):
        """Process bootloader message."""
        self.debug_log(f"Got Bootloader message: !B:{msg}")
        ignore_rgb = self.config['ignore_reboot']
        if msg in ('00', '02'):
            if ignore_rgb:
                self.machine.events.post("fast_rgb_rebooted", msg=msg)
                self.error_log("FAST RGB processor rebooted. Ignoring.")
            else:
                self.error_log("FAST RGB processor rebooted.")
                self.machine.stop("FAST RGB processor rebooted")

    def update_leds(self):
        """Update all the LEDs connected to the RGB processor of a FAST Nano controller.

        This is done once per game loop for efficiency (i.e. all LEDs are sent as a single
        update rather than lots of individual ones).

        """
        dirty_leds = [led for led in self.platform.fast_leds.values() if led.dirty]

        if dirty_leds:
            msg = 'RS:' + ','.join(["%s%s" % (led.number, led.current_color) for led in dirty_leds])
            self.send_blind(msg)

    def start(self):
        """Start listening for commands and schedule watchdog."""
        self.reset()

        if self.config['led_hz'] > 30:
            self.config['led_hz'] = 30

        self._led_task = self.machine.clock.schedule_interval(
                        self.update_leds, 1 / self.config['led_hz'])

    def reset(self):
        """Reset the RGB processor."""
        self.send_blind('RF:0')
        self.send_blind('RA:000000')
        self.send_blind(f"RF:{Util.int_to_hex_string(self.config['led_fade_time'])}")

    def stopping(self):
        if self._led_task:
            self._led_task.cancel()
            self._led_task = None

        self.reset()