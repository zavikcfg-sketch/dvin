from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    choosing_room = State()
    choosing_check_in = State()
    choosing_check_out = State()
    confirming = State()


class TvilImportStates(StatesGroup):
    waiting_periods = State()
