import espnow, machine, network, time


class BaseState:
    """
    All states inherit from this class. The job of a State class is to:
    1. provide enter() and exit() commands that do stuff
    2. bind callbacks for button pushes and any other events that can happen

    So this BaseState class does a few nice things to make it easier to make a State,
    like automatically logging entry/exit, and binding callbacks for buttons.
    
    Subclasses should implement functionality by overriding any of the on_[something] methods.
    """

    def __init__(self, state_machine):
        self.state_machine = state_machine

    ## the following methods should be overridden by subclasses as needed

    def on_enter(self, **kwargs):
        pass

    def on_exit(self):
        pass

    def on_button_push(self, button_number):
        pass

    def on_button_release(self, button_number):
        pass

    def on_wifi_message(self, mac, text):
        pass

    ## the methods below here provide functionality and should be overridden with care

    def enter(self, **kwargs):
        self.log("entering...")
        self.bind_buttons()
        self.register_wifi_message_callback()
        self.on_enter(**kwargs)
        self.log("entered")

    def exit(self):
        self.log("exiting...")
        self.on_exit()
        self.unbind_buttons()
        self.clear_wifi_message_callback()
        self.log("exited")

    def bind_buttons(self):
        self.log("binding buttons...")
        for button in self.state_machine.buttons:
            button.callback = self.button_callback

    def unbind_buttons(self):
        self.log("unbinding buttons...")
        for button in self.state_machine.buttons:
            button.callback = None

    def button_callback(self, pin):
        button_number = self.button_number_from_pin(pin)
        if pin.value() == 0:
            self.state_machine.lights[button_number].on()
            self.log("button push: %s" % button_number)
            self.on_button_push(button_number)
        if pin.value() == 1:
            self.state_machine.lights[button_number].off()
            self.log("button release: %s" % button_number)
            self.on_button_release(button_number)

    def button_number_from_pin(self, pin):
        for i, button in enumerate(self.state_machine.buttons):
            if button.pin == pin:
                return i

    def register_wifi_message_callback(self):
        self.state_machine.wifi.register_msg_callback(self.on_wifi_message)

    def clear_wifi_message_callback(self):
        self.state_machine.wifi.clear_callback()

    def log(self, msg):
        print("  %s: %s" % (self.__class__.__name__, msg))


class AwakeState(BaseState):
    """A simple state to jump into other states."""

    def on_button_push(self, button_number):
        self.log("button pushed: %s" % button_number)
        if button_number == 3:
            return self.state_machine.go_to_state("searching_for_opponent")

    def on_button_release(self, button_number):
        self.log("button released: %s" % button_number)
        if button_number == 2:
            return self.state_machine.go_to_state("simon_says_round_sync")
        elif button_number == 0:
            return self.state_machine.go_to_state("dj_mode")


class DJModeState(BaseState):
    """A state that just lets you play music. Exit it by hitting the reset button on the back."""

    pass


class SearchingForOpponentState(BaseState):
    """
    Sends out challenges over ESPNOW. When one is found, forward state.
    Button must be held down to remain in this state.
    """

    def on_enter(self):
        self.state_machine.timer.init(
            period=machine.random(750, 1500),
            mode=machine.Timer.PERIODIC,
            callback=self.broadcast,
        )

    def broadcast(self, timer):
        self.state_machine.wifi.broadcast("anyone there?")

    def on_wifi_message(self, mac, msg):
        if msg == b"anyone there?":  # challenge them!
            challenge_str = "".join(str(i) for i in generate_simon_says_challenge())
            self.state_machine.wifi.send_message(mac, "challenge: %s" % challenge_str)
            return
        elif msg.startswith(b"challenge: "):  # accept the challenge by echoing back
            challenge_str = msg.split(b" ")[1]
            self.state_machine.wifi.send_message(
                mac, "challenge_accepted: %s" % challenge_str.decode("utf-8")
            )
            self.clear_wifi_message_callback()

            return self.state_machine.go_to_state(
                "simon_says_challenge",
                challenge=[int(chr(digit)) for digit in challenge_str],
                multiplayer=True,
            )
        elif msg.startswith(b"challenge_accepted: "):  # they accepted our challenge
            self.clear_wifi_message_callback()
            challenge_str = msg.split(b" ")[1]
            return self.state_machine.go_to_state(
                "simon_says_challenge",
                challenge=[int(chr(digit)) for digit in challenge_str],
                multiplayer=True,
            )

    def on_button_release(self, button_number):
        if button_number == 3:
            return self.state_machine.go_to_state("awake")


class SimonSaysRoundSyncState(BaseState):
    MAX_ROUNDS = 4

    def on_enter(self, opponent_mac=None, rnd=0, did_lose=False):
        self.unbind_buttons()  # buttons do nothing in this state

        self.rnd = rnd
        self.opponent_mac = opponent_mac
        if self.opponent_mac:
            # multiplayer

            # spam my round results while waiting for the opponent's to come in
            self.state_machine.timer.init(
                period=machine.random(250, 750),
                mode=machine.Timer.PERIODIC,
                callback=self.send_game_state,
            )
        else:
            # single player

            if did_lose:
                # end the game as a loser
                self.state_machine.lights.all_blink(times=2)
                return self.state_machine.go_to_state("awake")  # TODO - go where?
            elif rnd >= SimonSaysRoundSyncState.MAX_ROUNDS:
                # end the game as a winner
                self.state_machine.lights.confetti(times=10)
                return self.state_machine.go_to_state("awake")  # TODO - go where?
            else:
                # go to next round
                return self.next_round(rnd)

    def next_round(self, rnd):
        # flash lights before next round
        self.state_machine.lights.all_blink(times=2)
        time.sleep(0.2)

        return self.state_machine.go_to_state(
            "simon_says_challenge",
            challenge=self.create_new_challenge(length=rnd + 3),
            rnd=rnd + 1,
        )

    def send_game_state(self):
        pass

    def on_wifi_message(self, mac, msg):
        if not msg.startswith(b"game_state: ") or self.opponent_mac != mac:
            return

    def create_new_challenge(self, length):
        return [machine.random(0, 3) for _ in range(0, length)]


class SimonSaysChallengeState(BaseState):
    def on_enter(self, challenge, rnd):
        self.unbind_buttons()  # buttons do nothing in this state

        # display the challenge
        for num in challenge[:-1]:
            self.state_machine.lights[num].blink(duration=0.3)
            time.sleep(0.2)
        # handle the last one outside the forloop so we don't end on a sleep
        self.state_machine.lights[challenge[-1]].blink(duration=0.3)

        # let the user start their guessing
        self.state_machine.go_to_state(
            "simon_says_guessing", challenge=challenge, rnd=rnd
        )


class SimonSaysGuessingState(BaseState):
    def on_enter(self, challenge, rnd):
        self.challenge = challenge
        self.rnd = rnd
        self.current_guess_ct = 0

        # variables set in on_button_push and used in on_button_release to indicate win/loss
        self.round_over = False
        self.wrong_guess = False

        # set the expiry timeout for max time between presses
        self.state_machine.timer.init(
            period=5000, mode=machine.Timer.ONE_SHOT, callback=self.end_round
        )

    def end_round(self, *args):
        self.unbind_buttons()  # disable buttons from doing anything

        is_timeout = len(args) != 0  # if we arrived here from the timer callback

        did_lose = self.wrong_guess or is_timeout
        if did_lose:
            # show correct guess
            correct_guess = self.challenge[self.current_guess_ct]
            self.state_machine.lights[correct_guess].blink(duration=0.2, times=2)

        self.state_machine.go_to_state(
            "simon_says_round_sync", rnd=self.rnd, did_lose=did_lose
        )

    def on_button_push(self, button_number):
        """
        We record the result on button push, but we don't end the round until button release.
        Gameplay feels better that way.
        """
        self.state_machine.timer.reshoot()  # reset the expiry timer

        if self.round_over or self.wrong_guess:
            # the round is over but they haven't let go of the last button yet, so do nothing
            return

        if self.challenge[self.current_guess_ct] == button_number:
            # correct guess
            self.current_guess_ct += 1

            if self.current_guess_ct == len(self.challenge):
                self.round_over = True
        else:
            # wrong guess
            self.wrong_guess = True
            self.round_over = True

    def on_button_release(self, button_number):
        if self.round_over:
            self.end_round()
