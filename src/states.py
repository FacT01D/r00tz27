import espnow, machine, network, time

BROADCAST_ADDR = b"\xFF" * 6
wifi = network.WLAN(network.AP_IF)


class BaseState:
    """
    All states inherit from this class. The job of a State class is to:
    1. provide enter() and exit() commands that do stuff
    2. bind callbacks for button pushes and any other events that can happen

    So this BaseState class does a few nice things to make it easier to make a State,
    like automatically logging entry/exit, and binding/unbinding callbacks for buttons.
    
    Subclasses should implement functionality by overriding any of the on_[something] methods.
    """

    def __init__(self, state_machine):
        self.state_machine = state_machine

    ## the following methods should be overridden by subclasses as needed

    def on_enter(self):
        pass

    def on_exit(self):
        pass

    def on_button_push(self, button_number):
        pass

    def on_button_release(self, button_number):
        pass

    ## the methods below here provide functionality and should be overridden with care

    def enter(self):
        self.log("entering...")
        self.bind_buttons()
        self.on_enter()
        self.log("entered")

    def exit(self):
        self.log("exiting...")
        self.on_exit()
        self.log("exited")

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
        print("  %s: %s" % (self.__class__.__name__, msg))


class IdleState(BaseState):
    """A simple state that doesn't really do anything interesting."""

    def on_button_release(self, button_number):
        self.state_machine.go_to_state("searching_for_opponent")


class SearchingForOpponentState(BaseState):
    """Sends out challenges over ESPNOW. When one is found, forward state."""

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
    """
    A possible opponent has been identified, so talk to their mac address directly
    to work out specifics. Once acknowledged, forward state to start the game.
    """

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
    """The actual Simon Says game itself."""

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
            challenge.append(machine.random(0, len(self.buttons) - 1))
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
