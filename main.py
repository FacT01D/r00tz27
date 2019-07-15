from machine import Pin, PWM
import time, random


class Button:
    """
    A button that does something when pushed.
    Usage:
        def callback(pin): print("Pushed: %s" % pin)
        button = Button(pin=27, on_push=callback)
    When pushed: "Pushed: Pin(27) mode=IN, PULL_UP, irq=IRQ_FALLING, debounce=0, actTime=0"
    """

    def __init__(self, pin, handler=None, trigger=Pin.IRQ_FALLING, *args, **kwargs):
        if not handler:
            handler = print

        self.pin = Pin(
            pin, Pin.IN, Pin.PULL_UP, handler=handler, trigger=trigger, *args, **kwargs
        )

    def disable(self):
        self.pin.init(handler=None, trigger=Pin.IRQ_DISABLE)


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

    def beep(self, note, duration):
        time.sleep(50 / 1000)
        self.pwm.init(freq=Buzzer.NOTES[note], duty=50)

        synced_light = None
        if self.lights:
            synced_light = random.choice(self.lights)
            synced_light.on()

        time.sleep(duration / 1000)

        synced_light.off() if synced_light else None

        self.pwm.duty(0)

    def silence(self):
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

    def __init__(self, pin=13):
        self.pin = Pin(pin, Pin.OUT)

    def on(self):
        self.pin.value(1)

    def off(self):
        self.pin.value(0)

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

    def __init__(self, led_pins=None):
        if not led_pins:
            led_pins = [26, 25, 4, 21]

        self.leds = [LED(pin) for pin in led_pins]

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
            last_led = random.choice([led for led in self.leds if led != last_led])
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


class SimonSays:
    def __init__(self, button_pins=None):
        if not button_pins:
            button_pins = [27, 33, 15, 32]

        self.buttons = [
            Button(
                pin,
                handler=self.button_callback,
                trigger=Pin.IRQ_ANYEDGE,
                debounce=1000,
            )
            for pin in button_pins
        ]

        self.lights = Lights()

        self.state = None
        self.current_challenge = []
        self.current_guess_ct = 0

        self.board_led = LED(13)
        self.board_led.on()

    def button_callback(self, pin):
        button_number = self.button_number_from_pin(pin)
        if pin.value() == 0:
            self.on_button_push(button_number)
        if pin.value() == 1:
            self.on_button_release(button_number)

    def button_number_from_pin(self, pin):
        for i, button in enumerate(self.buttons):
            if button.pin == pin:
                return i

    def on_button_push(self, button_number):
        if self.state is None or self.state == "losing":
            self.lights[button_number].on()
        elif self.state == "guessing":
            self.lights[button_number].on()
            self.count_guess(button_number)

    def on_button_release(self, button_number):
        self.lights[button_number].off()

        if self.state is None:
            self.board_led.off()
            self.start_game()
        elif self.state == "winning":
            self.win_round()
        elif self.state == "losing":
            self.lights[button_number].on()
            self.lose()

    def start_game(self):
        self.state = "launching"
        self.lights.cycle(times=1)
        time.sleep(1)
        self.challenge()

    def challenge(self):
        self.state = "challenging"
        self.current_challenge = self.build_new_challenge(
            length=len(self.current_challenge) + 1
            if self.current_challenge
            else 3  # first round is 3 flashes
        )
        self.display_challenge(self.current_challenge)
        self.start_guessing()

    def build_new_challenge(self, length):
        challenge = []
        while length:
            length -= 1
            challenge.append(random.randrange(0, len(self.buttons)))
        return challenge

    def display_challenge(self, challenge):
        self.state = "displaying"
        for num in challenge:
            self.lights[num].blink(duration=0.4)
            time.sleep(0.2)

    def start_guessing(self):
        self.state = "guessing"
        self.current_guess_ct = 0

    def count_guess(self, pushed_button_number):
        if self.current_challenge[self.current_guess_ct] == pushed_button_number:
            self.current_guess_ct += 1

            if self.current_guess_ct == len(self.current_challenge):
                self.state = "winning"
        else:
            self.state = "losing"

    def win_round(self):
        self.lights.confetti(times=15)
        time.sleep(1)
        self.challenge()

    def lose(self):
        for button in self.buttons:
            button.disable()

        correct_guess = self.current_challenge[self.current_guess_ct]
        self.lights[correct_guess].blink(duration=0.2, times=2)
        self.lights.all_blink(times=max(2, len(self.current_challenge) - 3))
        time.sleep(0.1)
        self.__init__()


SimonSays()
