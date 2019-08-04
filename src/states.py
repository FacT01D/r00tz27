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
            self.on_button_push(button_number)
        if pin.value() == 1:
            self.state_machine.lights[button_number].off()
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
    """A simple state that doesn't really do anything interesting."""

    def on_button_release(self, button_number):
        self.state_machine.go_to_state("searching_for_opponent")


class SearchingForOpponentState(BaseState):
    """Sends out challenges over ESPNOW. When one is found, forward state."""

    def on_enter(self):
        self.state_machine.wifi.broadcast("anyone there?")

    def on_wifi_message(self, mac, msg):
        self.log("target acquired, challenge received: %s" % msg)
        self.state_machine.go_to_state("negotiating_with_opponent", opponent_mac=mac)


class NegotiatingWithOpponentState(BaseState):
    """
    A possible opponent has been identified, so talk to their mac address directly
    to work out specifics. Once acknowledged, forward state to start the game.
    """

    def on_enter(self, opponent_mac):
        self.opponent_mac = opponent_mac
        self.state_machine.wifi.send_message(self.opponent_mac, "let's start playing")

    def on_wifi_message(self, mac, text):
        if mac == self.opponent_mac and text == b"let's start playing":
            # here we explicitly clear the callback before sending an ACK so we don't end up
            # in an infinite loop of messages back and forth
            self.state_machine.wifi.clear_callback()
            self.state_machine.wifi.send_message(
                self.opponent_mac, "let's start playing"
            )
            self.state_machine.go_to_state("simon_says_challenge")


class SimonSaysChallengeState(BaseState):
    MAX_ROUNDS = 5

    def on_enter(self, challenge=None, round=1):
        if not challenge:
            # generate a new challenge
            challenge = [
                machine.random(0, len(self.state_machine.buttons) - 1)
                for _ in range(0, SimonSaysChallengeState.MAX_ROUNDS + 3)
            ]

        if round > SimonSaysChallengeState.MAX_ROUNDS:
            # game is over after winning the max number of rounds
            self.state_machine.lights.confetti(times=10)
            return self.state_machine.go_to_state("awake")  # TODO - go where?

        if round == 1:
            self.state_machine.lights.all_blink(times=2)

        # display the challenge
        current_round_challenge = challenge[0 : round + 2]
        for num in current_round_challenge:
            self.state_machine.lights[num].blink(duration=0.4)
            time.sleep(0.2)

        # let the user start their guessing
        self.state_machine.go_to_state(
            "simon_says_guessing", challenge=challenge, round=round
        )


class SimonSaysGuessingState(BaseState):
    def on_enter(self, challenge, round):
        self.challenge = challenge
        self.round = round
        self.current_guess_ct = 0

        self.round_over = False
        self.wrong_guess = False

    def on_button_push(self, button_number):
        """
        We record the result on button push, but we don't end the round until button release.
        Gameplay feels better that way.
        """
        if self.challenge[self.current_guess_ct] == button_number:
            # correct guess
            self.current_guess_ct += 1

            if self.current_guess_ct == self.round + 2:
                self.round_over = True
        else:
            # wrong guess
            self.wrong_guess = True
            self.round_over = True

    def on_button_release(self, button_number):
        if self.round_over:
            self.unbind_buttons()
            self.state_machine.lights.all_off()
            if self.wrong_guess:
                # game finished after wrong guess
                correct_guess = self.challenge[self.current_guess_ct]
                self.state_machine.lights[correct_guess].blink(duration=0.2, times=2)
                self.state_machine.lights.all_blink(times=2)
                self.state_machine.go_to_state("awake")  # TODO - go where?
            else:
                # round finished after successful guessing, but game isn't over yet
                self.state_machine.go_to_state(
                    "simon_says_challenge",
                    challenge=self.challenge,
                    round=self.round + 1,
                )


### IGNORE THE BELOW. SAVED FOR MY NOTES:
# class SimonSaysState(BaseState):

#     def __init__(self, state_machine):
#         self.state_machine = state_machine
#         self.lights = self.state_machine.lights
#         self.buttons = self.state_machine.buttons

#         self.state = None
#         self.current_challenge = []
#         self.current_guess_ct = 0

#     def on_button_push(self, button_number):
#         if self.state is None or self.state == "losing":
#             self.state_machine.lights[button_number].on()
#         elif self.state == "guessing":
#             self.lights[button_number].on()
#             self.count_guess(button_number)

#     def on_button_release(self, button_number):
#         self.lights[button_number].off()

#         if self.state is None:
#             self.start_game()
#         elif self.state == "winning":
#             self.win_round()
#         elif self.state == "losing":
#             self.lights[button_number].on()
#             self.lose()

#     def enter(self):
#         self.start_game()

#     def start_game(self):
#         self.state = "launching"
#         self.lights.cycle(times=1)
#         time.sleep(1)
#         self.challenge()

#     def challenge(self):
#         self.state = "challenging"
#         self.current_challenge = self.build_new_challenge(
#             length=len(self.current_challenge) + 1
#             if self.current_challenge
#             else 3  # first round is 3 flashes
#         )
#         self.display_challenge(self.current_challenge)
#         self.start_guessing()

#     def build_new_challenge(self, length):
#         challenge = []
#         while length:
#             length -= 1
#             challenge.append(machine.random(0, len(self.buttons) - 1))
#         return challenge

#     def display_challenge(self, challenge):
#         self.state = "displaying"
#         for num in challenge:
#             self.lights[num].blink(duration=0.4)
#             time.sleep(0.2)

#     def start_guessing(self):
#         self.state = "guessing"
#         self.current_guess_ct = 0

#     def count_guess(self, pushed_button_number):
#         if self.current_challenge[self.current_guess_ct] == pushed_button_number:
#             self.current_guess_ct += 1

#             if self.current_guess_ct == len(self.current_challenge):
#                 self.state = "winning"
#         else:
#             self.state = "losing"

#     def win_round(self):
#         self.lights.confetti(times=15)
#         time.sleep(1)
#         self.challenge()

#     def lose(self):
#         for button in self.buttons:
#             button.update(handler=None)

#         correct_guess = self.current_challenge[self.current_guess_ct]
#         self.lights[correct_guess].blink(duration=0.2, times=2)
#         self.lights.all_blink(times=max(2, len(self.current_challenge) - 3))
#         time.sleep(0.1)
#         self.state_machine.go_to_state("idle")
