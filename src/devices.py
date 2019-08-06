# This file contains abstractions for the hardware on the board.

from machine import Pin, PWM, random
import espnow, math, network, time

from .rtttl import RTTTL
from .songs import random_song


def random_choice(from_list):
    """A helper function to randomly pick an item from a list"""
    idx = random(0, len(from_list) - 1)
    return from_list[idx]


class Button:
    """
    A button that does something when pushed.
    Usage:
        def callback(pin): print("Pushed: %s" % pin)
        button = Button(pin=27, on_push=callback)
    When pushed: "Pushed: Pin(27) mode=IN, PULL_UP, irq=IRQ_FALLING, debounce=0, actTime=0"
    """

    def __init__(self, pin, handler=None, trigger=Pin.IRQ_FALLING, *args, **kwargs):
        self.callback = handler
        self.pin = Pin(
            pin,
            Pin.IN,
            Pin.PULL_UP,
            handler=self.handler,
            trigger=trigger,
            *args,
            **kwargs
        )

    def handler(self, *args, **kwargs):
        if self.callback:
            self.callback(*args, **kwargs)

    def disable(self):
        self.pin.init(handler=None, trigger=Pin.IRQ_DISABLE)

    def update(self, *args, **kwargs):
        self.pin.init(**kwargs)


class Buzzer:
    """
    A buzzer that plays musical notes.
    Usage:
        buzzer = Buzzer()
        buzzer.force()
    """

    NOTES = dict(
        c=261,
        d=294,
        e=329,
        f=349,
        g=391,
        gS=415,
        a=440,
        aS=455,
        b=466,
        cH=523,
        cSH=55,
        dH=587,
        dSH=62,
        eH=659,
        fH=698,
        fSH=74,
        gH=784,
        gSH=83,
        aH=880,
    )

    def __init__(self, pin=12, sync_with=None):
        self.pwm = PWM(pin, duty=0)
        self.lights = sync_with

    def beep(self, note, duration=150):
        time.sleep(50 / 1000)
        self.pwm.init(freq=Buzzer.NOTES[note], duty=50)

        synced_light = None
        if self.lights:
            synced_light = random_choice(self.lights)
            synced_light.on()

        time.sleep(duration / 1000)

        synced_light.off() if synced_light else None

        self.pwm.duty(0)

    def tone(self, freq, duration):
        freq = round(freq)
        duration = round(duration * 0.9)
        pause = round(duration * 0.1)

        if freq > 0:
            self.pwm.init(freq=freq, duty=50)

        time.sleep_ms(duration)
        self.pwm.duty(0)
        time.sleep_ms(pause)

    def random_song(self):
        tune = RTTTL(random_song())
        for freq, duration in tune.notes():
            self.tone(freq, duration)

    def on(self, note):
        self.pwm.init(freq=Buzzer.NOTES[note], duty=50)

    def off(self):
        self.pwm.duty(0)

    def force(self):
        self.beep("a", 500)
        self.beep("a", 500)
        self.beep("a", 500)
        self.beep("f", 350)
        self.beep("cH", 150)
        self.beep("a", 500)
        self.beep("f", 350)
        self.beep("cH", 150)
        self.beep("a", 650)


class LED:
    """
    A single LED connected to a pin.
    Usage:
        led = LED(pin=26)
        led.on()
    """

    def __init__(self, pin=13, buzzer=None, note=None):
        self.pin = Pin(pin, Pin.OUT)

        self.buzzer = None
        if buzzer and note:
            self.buzzer = buzzer
            self.note = note

    def on(self):
        self.pin.value(1)
        if self.buzzer:
            self.buzzer.on(self.note)

    def off(self):
        self.pin.value(0)
        if self.buzzer:
            self.buzzer.off()

    def blink(self, duration=0.1, times=1):
        while times:
            times -= 1
            self.on()
            time.sleep(duration)
            self.off()

            if times > 0:
                time.sleep(duration)


class Lights:
    """
    A collection of our four LEDs.
    Usage:
        lights = Lights()
        lights.confetti()
        lights[0].blink()
    """

    def __init__(self, sync_with_buzzer=None):
        led_pins = [26, 25, 4, 21]
        buzzer_notes = ["a", "b", "d", "g"]

        self.leds = [
            LED(pin, buzzer=sync_with_buzzer, note=note)
            for pin, note in zip(led_pins, buzzer_notes)
        ]
        self.buzzer = sync_with_buzzer

    def __getitem__(self, key):
        return self.leds[key]

    def __len__(self):
        return len(self.leds)

    def cycle(self, times=1):
        while times:
            times -= 1

            for led in self.leds:
                led.blink()

            time.sleep(0.1)

            for led in reversed(self.leds):
                led.blink()

            time.sleep(0.1)

    def confetti(self, times=50):
        last_led = None
        while times:
            times -= 1
            last_led = random_choice([led for led in self.leds if led != last_led])
            last_led.blink()

    def all_blink(self, times=5):
        while times:
            times -= 1
            time.sleep(0.3)
            for led in self.leds:
                led.on()
            time.sleep(0.3)
            for led in self.leds:
                led.off()

    def all_off(self):
        for led in self.leds:
            led.off()

    def all_on(self):
        for led in self.leds:
            led.on()

    def flash_eyes(self):
        p0 = PWM(self.leds[0].pin, freq=1000)
        p1 = PWM(self.leds[2].pin, freq=1000)
        for i in range(20):
            d = ((int(math.sin(i / 10 * math.pi) * 500 + 500)) / 1024.0) * 100.0
            p0.duty(d)
            p1.duty(d)
            time.sleep_ms(50)

        p0.duty(0)
        p1.duty(0)


class WiFi:
    """
    Wraps board-to-board wireless comms (including ESPNOW) into a nicer API.
    """

    BROADCAST_ADDR = b"\xFF" * 6

    def __init__(self):
        self.msg_callbacks = []
        self.wlan = network.WLAN(network.AP_IF)
        self.peer_list = []

    def on(self):
        self.wlan.active(True)
        self.wlan.config(channel=1)
        self.wlan.config(protocol=network.MODE_LR)

        espnow.init()
        espnow.set_pmk("0123456789abcdef")
        espnow.set_recv_cb(self.on_espnow_message)
        self.add_espnow_peer(WiFi.BROADCAST_ADDR)

    def off(self):
        espnow.deinit()
        self.wlan.active(False)
        self.peer_list = []

    def send_message(self, mac, body):
        print("->msg send %s (from %s)" % (body, mac))

        self.add_espnow_peer(mac)
        text = "r00tz27 %s" % body
        espnow.send(mac, text)

    def broadcast(self, body):
        text = "r00tz27 %s" % body
        espnow.send(WiFi.BROADCAST_ADDR, text)

    def on_espnow_message(self, message):
        mac, text = message

        if not text.startswith(b"r00tz27"):
            # not a message we can understand
            return

        _, *body = text.split(b" ")
        body = b" ".join(body)

        print("<-msg recv %s (from %s)" % (body, mac))

        for callback in self.msg_callbacks:
            callback(mac, body)

    def add_espnow_peer(self, addr):
        if addr in self.peer_list:
            return

        self.peer_list.append(addr)

        try:
            espnow.add_peer(self.wlan, addr)
        except OSError as err:
            if str(err) == "ESP-Now Peer Exists":
                # this error means the opponent mac is already in the peer list,
                # which is fine, so we can continue
                pass
            else:
                # some other unexpected OSError
                raise

    def register_msg_callback(self, callback):
        self.msg_callbacks.append(callback)

    def clear_callback(self):
        self.msg_callbacks = []
