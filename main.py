from machine import Pin, PWM, random
import collections, network, time, espnow


def random_choice(from_list):
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
        if not handler:
            handler = print

        self.pin = Pin(
            pin, Pin.IN, Pin.PULL_UP, handler=handler, trigger=trigger, *args, **kwargs
        )

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

    def beep(self, note, duration):
        time.sleep(50 / 1000)
        self.pwm.init(freq=Buzzer.NOTES[note], duty=50)

        synced_light = None
        if self.lights:
            synced_light = random_choice(self.lights)
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


BROADCAST_ADDR = b"\xFF" * 6
wifi = network.WLAN(network.AP_IF)


class BaseState:
    def __init__(self, state_machine):
        self.state_machine = state_machine

    def enter(self):
        self.log("entering...")
        self.bind_buttons()
        self.on_enter()
        self.log("entered")

    def exit(self):
        self.log("exiting...")
        self.on_exit()
        self.log("exited")

    def on_enter(self):
        pass

    def on_exit(self):
        pass

    def on_button_push(self, button_number):
        pass

    def on_button_release(self, button_number):
        pass

    def unbind_buttons(self):
        self.log("unbinding buttons...")
        for button in self.state_machine.buttons:
            button.update(handler=None)

    def bind_buttons(self):
        self.log("binding buttons...")
        for button in self.state_machine.buttons:
            button.update(handler=self.button_callback)

    def button_callback(self, pin):
        button_number = self.button_number_from_pin(pin)
        if pin.value() == 0:
            self.state_machine.lights[button_number].on()
            self.on_button_push(button_number)
        if pin.value() == 1:
            self.state_machine.lights[button_number].off()
            self.on_button_release(button_number)

    def button_number_from_pin(self, pin):
        for i, button in enumerate(self.state_machine.buttons):
            if button.pin == pin:
                return i

    def log(self, msg):
        print("%s: %s" % (self.__class__.__name__, msg))


class IdleState(BaseState):
    def on_button_release(self, button_number):
        self.state_machine.go_to_state("searching_for_opponent")


class SearchingForOpponentState(BaseState):
    def on_enter(self):
        wifi.active(True)
        wifi.config(channel=1)
        wifi.config(protocol=network.MODE_LR)

        espnow.deinit()  # in case espnow was already init'd -- a no-op if not
        espnow.init()
        espnow.set_pmk("0123456789abcdef")
        espnow.set_recv_cb(self.on_message_received)

        espnow.add_peer(wifi, BROADCAST_ADDR)

    def on_button_release(self, button_number):
        self.log("sending challenge...")
        espnow.send(BROADCAST_ADDR, "anyone there?")

    def on_message_received(self, msg):
        mac, body = msg
        self.log("target acquired, challenge received: %s" % body)
        self.state_machine.go_to_state("negotiating_with_opponent", opponent_mac=mac)

    def on_exit(self):
        espnow.set_recv_cb(None)  # clear the callback because this state is done


class NegotiatingWithOpponentState(BaseState):
    def __init__(self, opponent_mac, *args, **kwargs):
        super(NegotiatingWithOpponentState, self).__init__(*args, **kwargs)
        self.opponent_mac = opponent_mac
        try:
            espnow.add_peer(wifi, opponent_mac)
        except OSError as err:
            if str(err) == "ESP-Now Peer Exists":
                # this error means the opponent mac is already in the peer list,
                # which is fine, so we can continue
                pass
            else:
                # some other unexpected OSError
                raise

    def on_enter(self):
        espnow.set_recv_cb(self.on_message_received)
        espnow.send(self.opponent_mac, "let's start playing")

    def on_message_received(self, msg):
        mac, text = msg
        self.log("got a message during negotiations: %s" % text)

        if text == b"let's start playing":
            espnow.set_recv_cb(None)  # we don't need the callback anymore
            espnow.send(self.opponent_mac, "let's start playing")
            self.state_machine.go_to_state("playing_simon_says")


class SimonSaysState(BaseState):
    def __init__(self, state_machine):
        self.state_machine = state_machine
        self.lights = self.state_machine.lights
        self.buttons = self.state_machine.buttons

        self.state = None
        self.current_challenge = []
        self.current_guess_ct = 0

    def on_button_push(self, button_number):
        if self.state is None or self.state == "losing":
            self.state_machine.lights[button_number].on()
        elif self.state == "guessing":
            self.lights[button_number].on()
            self.count_guess(button_number)

    def on_button_release(self, button_number):
        self.lights[button_number].off()

        if self.state is None:
            self.start_game()
        elif self.state == "winning":
            self.win_round()
        elif self.state == "losing":
            self.lights[button_number].on()
            self.lose()

    def enter(self):
        self.start_game()

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
            challenge.append(random(0, len(self.buttons) - 1))
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
            button.update(handler=None)

        correct_guess = self.current_challenge[self.current_guess_ct]
        self.lights[correct_guess].blink(duration=0.2, times=2)
        self.lights.all_blink(times=max(2, len(self.current_challenge) - 3))
        time.sleep(0.1)
        self.state_machine.go_to_state("idle")


class StateMachine:
    def __init__(self, initial_state="idle"):
        self.states = {
            "idle": IdleState,
            "searching_for_opponent": SearchingForOpponentState,
            "negotiating_with_opponent": NegotiatingWithOpponentState,
            "playing_simon_says": SimonSaysState,
        }

        BUTTON_PINS = [27, 33, 15, 32]
        self.buttons = [
            Button(pin, trigger=Pin.IRQ_ANYEDGE, debounce=1000) for pin in BUTTON_PINS
        ]

        self.lights = Lights()
        self.board_led = LED(13)
        self.board_led.on()

        self.current_state = None
        self.go_to_state(initial_state)

    def go_to_state(self, name, **kwargs):
        print(
            "*** STATE TRANSITION: %s -> %s"
            % (
                self.current_state.__class__.__name__ if self.current_state else None,
                self.states[name].__name__,
            )
        )

        if self.current_state:
            self.current_state.exit()

        self.current_state = self.states[name](state_machine=self, **kwargs)
        self.current_state.enter()


state_machine = StateMachine(initial_state="searching_for_opponent")
