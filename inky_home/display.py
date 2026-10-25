import logging
import threading
import time
from datetime import timedelta

from .palette import indexed_image

log = logging.getLogger(__name__)


class PreviewDisplay:
    mode = "preview"
    def show(self, image):
        pass
    def close(self):
        pass


class InkyDisplay:
    mode = "hardware"
    def __init__(self):
        # Initialize inside the display worker, so a disconnected panel or missing
        # interface leaves the web controls and diagnostics available.
        self.device = None

    def show(self, image):
        if self.device is None:
            from inky.auto import auto
            device = auto()
            if tuple(device.resolution) != (600, 400):
                raise RuntimeError(f"Expected a 600×400 Inky, found {device.resolution}")
            self.device = device
        # The E640 driver recognizes this exact six-color palette and disables
        # dithering, keeping black text solid instead of scattering ink dots.
        self.device.set_image(indexed_image(image))
        self.device.show()

    def close(self):
        pass


class Buttons:
    """BCM pin mapping from Pimoroni's Spectra 6 example. No GPIO imports on Mac."""
    def __init__(self, callback):
        import gpiod
        import gpiodevice
        from gpiod.line import Bias, Direction, Edge
        chip = gpiodevice.find_chip_by_platform()
        self.offsets = [chip.line_offset_from_id(pin) for pin in (5, 6, 16, 24)]
        settings = gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_UP,
                                     edge_detection=Edge.FALLING)
        self.request = chip.request_lines(consumer="inky-home-buttons",
                                         config=dict.fromkeys(self.offsets, settings))
        self.callback = callback
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run, name="buttons", daemon=True)
        self.last = {}
        self.thread.start()

    def run(self):
        try:
            while not self.stop.is_set():
                if not self.request.wait_edge_events(timeout=timedelta(seconds=0.5)):
                    continue
                for event in self.request.read_edge_events():
                    label = "ABCD"[self.offsets.index(event.line_offset)]
                    now = time.monotonic()
                    if now - self.last.get(label, -1) < 0.25:
                        continue
                    self.last[label] = now
                    try:
                        self.callback(label)
                    except Exception:
                        log.exception("Button action failed")
        except Exception:
            log.exception("Button listener stopped; restart service to recover GPIO")

    @property
    def healthy(self):
        return self.thread.is_alive()

    def close(self):
        self.stop.set()
        self.thread.join(timeout=2)
        if not self.thread.is_alive():
            self.request.release()
