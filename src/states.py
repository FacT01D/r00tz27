import espnow, json, machine, network, random, time


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
        self.last_wifi_message_received = None  # for deduping

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
        """If you need this method, make sure to set USE_WIFI = True on the child"""
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

    def wifi_message_callback(self, message):
        print("<-msg recv " + str(message))

        mac, text = message

        if not text.startswith(b"r00tz27 "):
            # not a message we can understand
            return

        body = text[len(b"r00tz27 ") :]  # strip the leading word

        self.log("Processing wifi message: %s" % body)

        if self.last_wifi_message_received == (mac, body):
            self.log("Dropping message as dupe")
            return

        self.last_wifi_message_received = (mac, body)
        self.on_wifi_message(mac, body)

    def register_wifi_message_callback(self):
        if hasattr(self, "USE_WIFI"):
            self.log("binding wifi...")
            self.state_machine.wifi.register_msg_callback(self.wifi_message_callback)

    def clear_wifi_message_callback(self):
        if hasattr(self, "USE_WIFI"):
            self.log("unbinding wifi...")
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
        elif button_number == 1:
            time.sleep(0.5)
            return self.state_machine.buzzer.random_song()


class DJModeState(BaseState):
    """A state that just lets you play music. Exit it by hitting the reset button on the back."""

    pass


class SearchingForOpponentState(BaseState):
    """
    Sends out challenges over ESPNOW. When one is found, forward state.
    Button must be held down to remain in this state.
    """

    USE_WIFI = True

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
            seed = machine.random(0, 999999)
            self.state_machine.wifi.send_message(mac, "challenge: %s" % seed)
            return  # wait for a response message
        elif msg.startswith(b"challenge: "):  # accept the challenge by echoing back
            seed_str = msg.split(b" ")[1]
            seed = int(seed_str)

            self.state_machine.wifi.send_message(
                mac, "challenge_accepted: %s" % seed_str.decode("utf-8")
            )
            self.clear_wifi_message_callback()  # just to make sure this isnt triggered again

            return self.state_machine.go_to_state(
                "simon_says_round_sync", multiplayer_info=(mac, seed)
            )
        elif msg.startswith(b"challenge_accepted: "):  # they accepted our challenge
            self.clear_wifi_message_callback()  # just to make sure this isnt triggered again

            seed = int(msg.split(b" ")[1])

            return self.state_machine.go_to_state(
                "simon_says_round_sync", multiplayer_info=(mac, seed)
            )

    def on_button_release(self, button_number):
        if button_number == 3:
            return self.state_machine.go_to_state("awake")


class SimonSaysRoundSyncState(BaseState):
    MAX_ROUNDS = 4
    USE_WIFI = True

    def on_enter(self, rnd=0, did_lose=False, multiplayer_info=None):
        self.unbind_buttons()  # buttons do nothing in this state

        self.rnd = rnd
        self.did_lose = did_lose
        self.multiplayer_info = multiplayer_info

        if self.multiplayer_info:
            mac, seed = self.multiplayer_info

            if rnd == 0:
                # first round, seed the random number generator
                random.seed(seed)

            self.state_machine.quiet_lights.all_on()

            # send state to opponent -- if they aren't listening yet,
            # we'll send it again when they send us their state
            return self.send_game_state()

            # TODO -- expire this state if we lose contact with the opponent somehow
        else:
            # single player

            if rnd == 0:
                # first round, seed the random number generator with an actual random number
                random.seed(machine.random(0, 99999))

            return self.handle_round()

    def create_new_challenge(self, length):
        return [random.randint(0, 3) for _ in range(0, length)]

    def handle_round(self):
        if self.did_lose:
            # end the game as a loser
            self.state_machine.lights.all_blink(times=2)
            return self.game_over()
        elif self.rnd >= SimonSaysRoundSyncState.MAX_ROUNDS:
            # end the game as a winner
            self.state_machine.lights.confetti(times=10)
            return self.game_over()
        else:
            # go to next round after flashing lights
            self.state_machine.lights.all_blink(times=2)
            time.sleep(0.2)

            return self.state_machine.go_to_state(
                "simon_says_challenge",
                challenge=self.create_new_challenge(length=self.rnd + 3),
                rnd=self.rnd + 1,  # next round
                multiplayer_info=self.multiplayer_info,
            )

    def send_game_state(self):
        mac, seed = self.multiplayer_info
        game_state = {"round_finished": self.rnd, "did_lose": self.did_lose}

        self.state_machine.wifi.send_message(
            mac, "game_state: %s" % json.dumps(game_state)
        )

    def on_wifi_message(self, mac, msg):
        if not msg.startswith(b"game_state: ") or mac != self.multiplayer_info[0]:
            return  # not a message for us

        self.clear_wifi_message_callback()  # don't handle any more messages
        self.send_game_state()  # so the two boards react in sync
        self.state_machine.quiet_lights.all_off()

        json_blob = msg[len(b"game_state: ") :]  # truncate msg up to the json
        opponent = json.loads(json_blob)

        if opponent["round_finished"] != self.rnd:
            raise Exception("??? wtf ???")  # TODO - what do you do?

        if not self.did_lose and opponent["did_lose"]:  # you won
            return self.you_win()
        elif self.did_lose and not opponent["did_lose"]:  # you lost
            return self.you_lose()
        elif self.did_lose and opponent["did_lose"]:  # both lost
            return self.both_lose()
        else:  # both win
            return self.handle_round()  # go to the next round

    def you_win(self):
        self.state_machine.lights.confetti(times=10)
        return self.game_over()

    def you_lose(self):
        self.state_machine.lights.all_blink(times=2)
        return self.game_over()

    def both_lose(self):
        self.state_machine.lights.all_blink(times=4)
        return self.game_over()

    def game_over(self):
        return self.state_machine.go_to_state(
            "awake"
        )  # TODO - what is the correct thing here?


class SimonSaysChallengeState(BaseState):
    def on_enter(self, challenge, rnd, multiplayer_info):
        self.unbind_buttons()  # buttons do nothing in this state

        # quick pause before displaying the challenge
        time.sleep(0.5)

        # display the challenge
        for num in challenge[:-1]:
            self.state_machine.lights[num].blink(duration=0.3)
            time.sleep(0.2)
        # handle the last one outside the forloop so we don't end on a sleep
        self.state_machine.lights[challenge[-1]].blink(duration=0.3)

        # let the user start their guessing
        self.state_machine.go_to_state(
            "simon_says_guessing",
            challenge=challenge,
            rnd=rnd,
            multiplayer_info=multiplayer_info,
        )


class SimonSaysGuessingState(BaseState):
    def on_enter(self, challenge, rnd, multiplayer_info):
        self.challenge = challenge
        self.rnd = rnd
        self.multiplayer_info = multiplayer_info
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
            "simon_says_round_sync",
            rnd=self.rnd,
            did_lose=did_lose,
            multiplayer_info=self.multiplayer_info,
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
