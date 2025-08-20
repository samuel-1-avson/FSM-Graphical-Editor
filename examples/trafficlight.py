
# -*- coding: utf-8 -*-
"""
Auto-generated Python FSM by Brain State Machine Designer v2.0.0
FSM Name: TrafficLight
Generated on: 2025-08-18 15:51:06

This file is auto-generated. DO NOT EDIT MANUALLY — your changes may be overwritten.
"""

from __future__ import annotations

import logging
from typing import Any

try:
    from statemachine import StateMachine, State
except Exception as exc:
    raise RuntimeError(
        "Failed to import 'statemachine'. Please install 'python-statemachine'."
    ) from exc

__all__ = ["TrafficLight"]

logger = logging.getLogger(__name__)


class TrafficLight(StateMachine):
    """
    Auto-generated FSM from BSM Designer.
    """

    # --- State Definitions ---

    Green = State(
        name="Green",
        value="Green",
        initial=False,
        enter="on_enter_Green"
    )
    Yellow = State(
        name="Yellow",
        value="Yellow",
        initial=False,
        enter="on_enter_Yellow"
    )
    Red = State(
        name="Red",
        value="Red",
        initial=True,
        enter="on_enter_Red"
    )

    # --- Transition Definitions ---


    timer_green_expired = \Green.to(
        Yellow,
        on="on_timer_green_expired"
    )
    timer_red_expired = \Red.to(
        Green,
        on="on_timer_red_expired"
    )
    timer_yellow_expired = \Yellow.to(
        Red,
        on="on_timer_yellow_expired"
    )

    # --- Action and Condition Methods ---
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)



    def on_enter_Green(self) -> None:
        """Entry action for state "Green"."""
        
print('Light is GREEN')
        timer_start_tick = current_tick
        event_sent = False
    # NOTE: "During" actions for state "Green" are not directly supported.
    # Consider calling a method from your main loop when the FSM is in this state,
    # or creating a self-transition on an internal 'tick' event.
    # Example scaffold:
    # def during_Green(self) -> None:
    #     ...
# GREEN_DURATION = 5
    if not event_sent and current_tick >= timer_start_tick + GREEN_DURATION:
      sm.send('timer_green_expired')
      event_sent = True


    def on_enter_Yellow(self) -> None:
        """Entry action for state "Yellow"."""
        
print('Light is YELLOW')
        timer_start_tick = current_tick
        event_sent = False
    # NOTE: "During" actions for state "Yellow" are not directly supported.
    # Consider calling a method from your main loop when the FSM is in this state,
    # or creating a self-transition on an internal 'tick' event.
    # Example scaffold:
    # def during_Yellow(self) -> None:
    #     ...
# YELLOW_DURATION = 2
    if not event_sent and current_tick >= timer_start_tick + YELLOW_DURATION:
      sm.send('timer_yellow_expired')
      event_sent = True


    def on_enter_Red(self) -> None:
        """Entry action for state "Red"."""
        
print('Light is RED')
        timer_start_tick = current_tick
        event_sent = False
    # NOTE: "During" actions for state "Red" are not directly supported.
    # Consider calling a method from your main loop when the FSM is in this state,
    # or creating a self-transition on an internal 'tick' event.
    # Example scaffold:
    # def during_Red(self) -> None:
    #     ...
# RED_DURATION = 5
    if not event_sent and current_tick >= timer_start_tick + RED_DURATION:
      sm.send('timer_red_expired')
      event_sent = True


    def on_timer_yellow_expired(self) -> None:
        """Action for event "timer_yellow_expired" from "Yellow" to "Red"."""
        
print('Transition: Yellow to Red')


    def on_timer_green_expired(self) -> None:
        """Action for event "timer_green_expired" from "Green" to "Yellow"."""
        
print('Transition: Green to Yellow')


    def on_timer_red_expired(self) -> None:
        """Action for event "timer_red_expired" from "Red" to "Green"."""
        
print('Transition: Red to Green')


def _configure_logging(level: int = logging.INFO) -> None:
    """Simple console logging configuration for quick demos/tests."""
    if not logging.getLogger().handlers:
        logging.basicConfig(level=level, format="%(levelname)s:%(name)s:%(message)s")


if __name__ == "__main__":
    _configure_logging()
    fsm = TrafficLight()
    logger.info("Initial state: %s", fsm.current_state.id)

    # Trigger events as methods (recommended):
    # try:
    #     fsm.timer_yellow_expired()
    #     logger.info("State after event: %s", fsm.current_state.id)
    # except Exception as exc:
    #     logger.exception("Event failed: %s", exc)

    # Or, if supported by the library version, send by string name:
    # try:
    #     fsm.send("timer_yellow_expired")
    #     logger.info("State after send: %s", fsm.current_state.id)
    # except Exception as exc:
    #     logger.exception("Send failed: %s", exc)