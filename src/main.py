import machine

from .devices import Button, Buzzer, LED, Lights
from .states import (
    IdleState,
    SearchingForOpponentState,
    NegotiatingWithOpponentState,
    SimonSaysState,
)


class StateMachine:
    """
    The core abstraction of the whole board. At all times, the board is in a "State" that
    defines what the buttons do when pushed, and what the board is doing at that moment.

    Each State class defines an enter() method and an exit() method. When the State Machine
    enters a State, it calls the enter() method on that State. When we change state, it calls
    the exit() method on the old State, and then the enter() method on the new State.
    """

    def __init__(self, initial_state="idle"):
        self.states = {
            "idle": IdleState,
            "searching_for_opponent": SearchingForOpponentState,
            "negotiating_with_opponent": NegotiatingWithOpponentState,
            "playing_simon_says": SimonSaysState,
        }

        BUTTON_PINS = [27, 33, 15, 32]
        self.buttons = [
            Button(pin, trigger=machine.Pin.IRQ_ANYEDGE, debounce=1000)
            for pin in BUTTON_PINS
        ]

        self.lights = Lights()

        self.board_led = LED(13)  # the tiny red LED on the board itself
        self.board_led.on()  # turn it on for debug so we know our code is actually running

        self.current_state = None
        self.go_to_state(initial_state)

    def go_to_state(self, name, **kwargs):
        """Handle a state transition by calling exit() on the old state and enter() on the new"""

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
        self.current_state = self.states[name](state_machine=self, **kwargs)

        self.current_state.enter()  # call enter() on the new state


def run():
    """The function that gets run on boot"""

    state_machine = StateMachine(initial_state="searching_for_opponent")
