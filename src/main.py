import machine

from .devices import Button, Buzzer, LED, Lights, WiFi
from .states import (
    AwakeState,
    DJModeState,
    SearchingForOpponentState,
    NegotiatingWithOpponentState,
    SimonSaysChallengeState,
    SimonSaysGuessingState,
)


class StateMachine:
    """
    The core abstraction of the whole board. At all times, the board is in a "State" that
    defines what the buttons do when pushed, and what the board is doing at that moment.

    Each State class defines an enter() method and an exit() method. When the State Machine
    enters a State, it calls the enter() method on that State. When we change state, it calls
    the exit() method on the old State, and then the enter() method on the new State.

    As the overlord of states and state transitions, all hardware devices are properties of,
    and controlled thru, this State Machine.
    """

    def __init__(self, initial_state="awake"):

        ## all possible states of the board

        self.states = {
            "awake": AwakeState,
            "dj_mode": DJModeState,
            "searching_for_opponent": SearchingForOpponentState,
            "negotiating_with_opponent": NegotiatingWithOpponentState,
            "simon_says_challenge": SimonSaysChallengeState,
            "simon_says_guessing": SimonSaysGuessingState,
        }

        ## initialize hardware devices

        self.wifi = WiFi()
        self.wifi.on()

        BUTTON_PINS = [27, 33, 15, 32]
        self.buttons = [
            Button(pin, trigger=machine.Pin.IRQ_ANYEDGE, debounce=5000, acttime=2000)
            for pin in BUTTON_PINS
        ]

        self.buzzer = Buzzer()
        self.lights = Lights(sync_with_buzzer=self.buzzer)

        self.board_led = LED(13)  # the tiny red LED on the board itself
        self.board_led.on()  # turn it on for debug so we know our code is actually running

        self.state_change_timer = machine.Timer(1)
        self.timer = machine.Timer(2)

        self.current_state = None
        self.go_to_state(initial_state)

    def go_to_state(self, name, **kwargs):
        """
        We handle state transitions asynchronously. Rather than stopping anything running
        we give it 20ms before this timer callback fires and forwards the state. This will
        hopefully easily mitigate some nasty race conditions. This also allows us to call
        state_machine.go_to_state within a State's on_enter method without causing problems.
        """

        # some cleanup first
        self.timer.deinit()
        self.lights.all_off()

        def callback(timer):
            self._go_to_state(name, **kwargs)

        self.state_change_timer.init(
            period=20, mode=machine.Timer.ONE_SHOT, callback=callback
        )

    def _go_to_state(self, name, **kwargs):
        """
        Handle a state transition by calling exit() on the old state and enter() on the new.
        
        This method is usually called by the current state to forward us to the new state.
        The current state can pass named arguments to the enter methods of the new state:
          >>> state_machine.go_to_state("my_new_state", arg1=val1, foo=bar)
        """

        old_state_class_name = (
            self.current_state.__class__.__name__ if self.current_state else None
        )
        new_state_class_name = self.states[name].__name__
        print("State change: %s to %s" % (old_state_class_name, new_state_class_name))

        if self.current_state:
            self.current_state.exit()  # call the exit() method on the old state

        # init a new object of the State class, and give it this state machine object so
        # it can control the state machine's variables (e.g. remap button handlers) and
        # it can call go_to_state to the next state.
        # in a future design, instead of creating a new State object, we can reuse the
        # same ones.
        self.current_state = self.states[name](state_machine=self)

        self.current_state.enter(**kwargs)  # call enter() on the new state


def run():
    """The function that gets run on boot"""

    state_machine = StateMachine(initial_state="awake")
