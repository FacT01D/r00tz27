from .states import StateMachine


def run():
    state_machine = StateMachine(initial_state="searching_for_opponent")
