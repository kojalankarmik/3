"""
FSM состояния для Aiogram 3
"""

from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    """Состояния пользовательского сценария"""
    
    main_menu = State()
    
    # Wizard подбора квартиры
    wizard_dates = State()
    wizard_guests = State()
    wizard_district = State()
    wizard_budget = State()
    wizard_results = State()
    
    # Обратная связь
    contact_form_topic = State()
    contact_form_message = State()
    contact_form_contact = State()


class AdminStates(StatesGroup):
    """Состояния администратора"""
    
    main_menu = State()
    apartment_list = State()
    apartment_select = State()
    apartment_edit = State()
    publishing_menu = State()