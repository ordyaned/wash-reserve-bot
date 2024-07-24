import os
import sqlite3
import telebot
import tabulate
from threading import Timer
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup

TOKEN = '6453639963:AAG7QR5MH8PEYkxvlIxCN_5tTR1MRHNyUFo'
# TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

db = 'data/styleseat.db'
# unavailability_db = 'data/styleseat.db'
# db = os.getenv('DB_PATH')
def init_db():
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    date TEXT,
    start_time TEXT,
    end_time TEXT,
    service TEXT,
    price INTEGER,
    UNIQUE(date, start_time)
)''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS unavailabilities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            start_time TEXT,
            end_time TEXT
        )
    ''')
    conn.commit()
    conn.close()

# init_db()
# Conversation states

MENU, DATE, TIME, SERVICE, UNAVAILABILITY_DATE, UNAVAILABILITY_TIME, NAME, UPDATE_SERVICE = range(8)

def go_home(message):
    start(message)

def add_home_button(reply_markup):
    home_button = telebot.types.KeyboardButton('Home')
    reply_markup.add(home_button)
    return reply_markup


# Start command
@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    item_reserve = telebot.types.KeyboardButton('Book Appointment')
    item_history = telebot.types.KeyboardButton('Booking History')
    item_upcoming = telebot.types.KeyboardButton('Upcoming Appointments')
    item_cancel = telebot.types.KeyboardButton('Cancel Appointment')
    item_barber_view = telebot.types.KeyboardButton('Barber View')
    markup.add(item_reserve, item_history, item_upcoming, item_cancel)

    if message.from_user.username == 'ordyaned':
        markup.add(item_barber_view)

    bot.send_message(message.chat.id, 'Welcome to StyleSeat! \U0001F487 \nPlease choose an option below:',
                     reply_markup=markup)


# Barber view command
@bot.message_handler(func=lambda message: message.text.lower() == 'barber view', content_types=['text'])
def barber_view(message):
    if message.from_user.username != 'ordyaned':
        bot.send_message(message.chat.id, 'You do not have access to the Barber View.')
        return start(message)

    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    item_set_unavailable = telebot.types.KeyboardButton('Set Unavailable')
    item_view_unavailabilities = telebot.types.KeyboardButton('View Unavailabilities')
    item_cancel_unavailability = telebot.types.KeyboardButton('Cancel Unavailability')
    item_view_appointments = telebot.types.KeyboardButton('View Appointments')
    markup.add(item_set_unavailable, item_view_unavailabilities, item_cancel_unavailability, item_view_appointments)

    bot.send_message(message.chat.id, 'Barber View \U0001F468 \U0001F487 \nPlease choose an option below:',
                     reply_markup=markup)


@bot.message_handler(func=lambda message: message.text.lower() == 'view appointments', content_types=['text'])
def view_appointments(message):
    if message.from_user.username != 'ordyaned':
        bot.send_message(message.chat.id, 'You do not have access to view all appointments.')
        return start(message)

    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM appointments ORDER BY date, start_time')
        appointments = cursor.fetchall()

    if not appointments:
        bot.send_message(message.chat.id, 'No appointments found.')
        return start(message)

    appointments_message = 'All Appointments:\n'
    for appointment in appointments:
        appointments_message += f"\nID: {appointment[0]}\nUsername: {appointment[2]}\nDate: {appointment[3]}\nTime: {appointment[4]} - {appointment[5]}\nService: {appointment[6]}\nPrice: {appointment[7]} AMD\n"
    bot.send_message(message.chat.id, appointments_message)

    start(message)



# Set unavailable dates or times
@bot.message_handler(func=lambda message: message.text.lower() == 'set unavailable', content_types=['text'])
def set_unavailable(message):
    date_buttons = [
        telebot.types.KeyboardButton((datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d'))
        for i in range(30)
    ]
    reply_markup = add_home_button(ReplyKeyboardMarkup(one_time_keyboard=True).add(*date_buttons))
    bot.send_message(message.chat.id, '\U0001F4C5 Please select a date to set as unavailable: \U0001F4C5',
                     reply_markup=reply_markup)
    bot.register_next_step_handler(message, set_unavailability_date)


def set_unavailability_date(message):
    try:
        selected_date = message.text
        reply_markup = add_home_button(ReplyKeyboardMarkup(one_time_keyboard=True))
        reply_markup.add('30 minutes', '1 hour', '2 hours', '4 hours')
        bot.send_message(message.chat.id, 'For how long will you be unavailable?', reply_markup=reply_markup)
        bot.register_next_step_handler(message, select_unavailability_duration, selected_date)
    except ValueError:
        bot.send_message(message.chat.id, 'Invalid date format. Please use the format YYYY-MM-DD to select a date for unavailability.')
        start(message)

def select_unavailability_duration(message, selected_date):
    try:
        duration = message.text
        duration_minutes = {'30 minutes': 30, '1 hour': 60, '2 hours': 120, '4 hours': 240}[duration]
        end_time = (datetime.strptime('09:00', '%H:%M') + timedelta(minutes=duration_minutes)).strftime('%H:%M')
        time_buttons = [
            telebot.types.KeyboardButton(f'{start} - {end}')
            for start, end in get_time_slots()
            if (datetime.strptime(start, '%H:%M') + timedelta(minutes=duration_minutes)).strftime('%H:%M') <= '23:59'
        ]
        reply_markup = add_home_button(ReplyKeyboardMarkup(one_time_keyboard=True).add(*time_buttons))
        bot.send_message(message.chat.id, '\U0001F55C Please select a time period to set as unavailable: \U0001F55C', reply_markup=reply_markup)
        bot.register_next_step_handler(message, set_unavailability_time, selected_date, duration_minutes)
    except ValueError:
        bot.send_message(message.chat.id, 'Invalid duration selected.')
        start(message)

def set_unavailability_time(message, selected_date, duration_minutes):
    try:
        time_period = message.text
        start_time, end_time = time_period.split(' - ')
        end_time = (datetime.strptime(start_time, '%H:%M') + timedelta(minutes=duration_minutes)).strftime('%H:%M')

        with sqlite3.connect(db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO unavailabilities (date, start_time, end_time) VALUES (?, ?, ?)',
                (selected_date, start_time, end_time)
            )
            conn.commit()

        bot.send_message(message.chat.id, f'Unavailability set for {selected_date} from {start_time} to {end_time}. \U0001F604 \U00002705')
        start(message)
    except ValueError:
        bot.send_message(message.chat.id, 'Invalid time format. Please select a valid time for unavailability.')
        start(message)



# View unavailabilities
@bot.message_handler(func=lambda message: message.text.lower() == 'view unavailabilities', content_types=['text'])
def view_unavailabilities(message):
    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM unavailabilities ORDER BY date, start_time')
        unavailabilities = cursor.fetchall()

    if not unavailabilities:
        bot.send_message(message.chat.id, 'No unavailabilities set.')
        start(message)
        return

    table_headers = ['ID', 'Date', 'Start Time', 'End Time']
    unavailability_table = []
    for unavailability in unavailabilities:
        unavailability_table.append([str(unavailability[0]), unavailability[1], unavailability[2], unavailability[3]])
    html_table = tabulate.tabulate(unavailability_table, table_headers, tablefmt='grid')
    unavailability_message = f'Unavailabilities:\n <pre>{html_table}</pre>'
    bot.send_message(message.chat.id, unavailability_message, parse_mode='HTML')

    start(message)


# Booking logic to exclude unavailable times
def get_time_slots() -> list:
    slots = []
    for i in range(10, 19):
        slots.append((f'{i:02d}:00', (datetime.strptime(f'{i:02d}:00', '%H:%M') + timedelta(minutes=30)).strftime('%H:%M')))
        slots.append((f'{i:02d}:30', (datetime.strptime(f'{i:02d}:30', '%H:%M') + timedelta(minutes=30)).strftime('%H:%M')))
    return slots



@bot.message_handler(func=lambda message: message.text.lower() == 'book appointment', content_types=['text'])
def book_start(message):
    if not message.from_user.first_name:
        msg = bot.send_message(message.chat.id, 'Please enter your first name:')
        bot.register_next_step_handler(msg, get_first_name)
    else:
        proceed_to_date_selection(message, message.from_user.first_name)


def get_first_name(message):
    first_name = message.text
    proceed_to_date_selection(message, first_name)


def proceed_to_date_selection(message, first_name):
    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT date FROM unavailabilities WHERE start_time = "00:00" AND end_time = "23:59"')
        unavailable_dates = set(row[0] for row in cursor.fetchall())

    date_buttons = [
        telebot.types.KeyboardButton((datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d'))
        for i in range(7)
        if (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d') not in unavailable_dates
    ]
    reply_markup = ReplyKeyboardMarkup(one_time_keyboard=True).add(*date_buttons)
    bot.send_message(message.chat.id, '\U0001F4C5 Please select a date for the appointment: \U0001F4C5', reply_markup=reply_markup)
    bot.register_next_step_handler(message, book_date, first_name)



def book_date(message, first_name):
    try:
        selected_date = message.text
        time_slots = get_available_time_slots(selected_date)

        if not time_slots:
            bot.send_message(message.chat.id,
                             'No available time slots for the selected date. Please choose another date.')
            start(message)
            return

        time_buttons = [
            telebot.types.KeyboardButton(f'{start} - {end}')
            for start, end in time_slots
        ]

        reply_markup = ReplyKeyboardMarkup(one_time_keyboard=True).add(*time_buttons)
        bot.send_message(message.chat.id, '\U0001F55C Please select a time for the appointment: \U0001F55C',
                         reply_markup=reply_markup)

        bot.register_next_step_handler(message, book_time, first_name, selected_date)
    except ValueError:
        bot.send_message(message.chat.id,
                         'Invalid date format. Please use the format YYYY-MM-DD to select a date for the appointment.')
        start(message)


def get_available_time_slots(selected_date) -> list:
    all_slots = get_time_slots()
    available_slots = []

    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT start_time, end_time FROM unavailabilities WHERE date = ?', (selected_date,))
        unavailable_times = cursor.fetchall()
        cursor.execute('SELECT start_time, end_time FROM appointments WHERE date = ?', (selected_date,))
        booked_times = cursor.fetchall()

    for start, end in all_slots:
        slot_available = True
        for unavailable_start, unavailable_end in unavailable_times + booked_times:
            if (start >= unavailable_start and start < unavailable_end) or (end > unavailable_start and end <= unavailable_end):
                slot_available = False
                break
        if slot_available:
            available_slots.append((start, end))

    return available_slots



def book_time(message, first_name, selected_date):
    try:
        user_id = message.from_user.id
        username = first_name
        date = selected_date
        start_time, end_time = message.text.split(' - ')

        with sqlite3.connect(db) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM appointments WHERE date = ? AND start_time = ?', (date, start_time))
            existing_appointment = cursor.fetchone()

        if existing_appointment:
            bot.send_message(message.chat.id,
                             f'The selected time slot is already booked. Please choose another time. \U0001F55D')
            start(message)
            return

        reply_markup = ReplyKeyboardMarkup(one_time_keyboard=True)
        reply_markup.add('Haircut', 'Haircut + Beard')
        bot.send_message(message.chat.id, '\U0001F488 Please select a service: \U0001F488', reply_markup=reply_markup)

        bot.register_next_step_handler(message, book_service, user_id, username, date, start_time, end_time)
    except ValueError:
        bot.send_message(message.chat.id, 'Invalid time format. Please select a valid time for the appointment.')
        start(message)


def book_service(message, user_id, username, date, start_time, end_time):
    try:
        service = message.text
        price = 3000 if service == 'Haircut' else 5000

        with sqlite3.connect(db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO appointments (user_id, username, date, start_time, end_time, service, price) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (user_id, username, date, start_time, end_time, service, price))
            conn.commit()

        bot.send_message(message.chat.id,
                         f'Appointment booked for {date} from {start_time} to {end_time} for {service} ({price} AMD). \U0001F604 \U00002705')

        schedule_notification(user_id, date, start_time)

        start(message)
    except ValueError:
        bot.send_message(message.chat.id, 'Invalid selection. Please choose a valid service.')
        start(message)


# Schedule notification
def schedule_notification(user_id, date, start_time):
    appointment_time = datetime.strptime(f'{date} {start_time}', '%Y-%m-%d %H:%M')
    notification_time = appointment_time - timedelta(hours=1)
    delay = (notification_time - datetime.now()).total_seconds()
    Timer(delay, send_notification, [user_id, date, start_time]).start()


def send_notification(user_id, date, start_time):
    bot.send_message(user_id, f'Reminder: You have an appointment on {date} at {start_time} in 1 hour.')


# Change service
@bot.message_handler(func=lambda message: message.text.lower() == 'change service', content_types=['text'])
def change_service(message):
    user_id = message.from_user.id
    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM appointments WHERE user_id = ? AND date >= ?',
                       (user_id, datetime.now().strftime('%Y-%m-%d')))
        user_appointments = cursor.fetchall()
    appointment_ids_buttons = [
        telebot.types.KeyboardButton(str(i[0]))
        for i in user_appointments
    ]
    reply_markup = add_home_button(ReplyKeyboardMarkup(one_time_keyboard=True).add(*appointment_ids_buttons))

    table_headers = ['ID', 'Date', 'Time', 'Service']
    appointment_table = []
    for appointment in user_appointments:
        appointment_table.append([str(appointment[0]), appointment[3], appointment[4], appointment[6]])
    html_table = tabulate.tabulate(appointment_table, table_headers, tablefmt='grid')
    timetable_message = f'Please select an appointment to change service\U0001F488 \nYour appointments: \n <pre>{html_table}</pre>'

    bot.send_message(message.chat.id, timetable_message, reply_markup=reply_markup, parse_mode='HTML')
    bot.register_next_step_handler(message, update_service)


def update_service(message):
    selected_appointment = str(message.text)
    reply_markup = ReplyKeyboardMarkup(one_time_keyboard=True)
    reply_markup.add('Haircut', 'Haircut + Beard')
    bot.send_message(message.chat.id, '\U0001F488 Please select a new service: \U0001F488', reply_markup=reply_markup)
    bot.register_next_step_handler(message, save_updated_service, selected_appointment)


def save_updated_service(message, selected_appointment):
    try:
        new_service = message.text
        new_price = 3000 if new_service == 'Haircut' else 5000

        with sqlite3.connect(db) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE appointments SET service = ?, price = ? WHERE id = ?',
                           (new_service, new_price, selected_appointment))
            conn.commit()

        bot.send_message(message.chat.id, f'Service updated to {new_service} ({new_price} AMD). \U0001F604 \U00002705')
        start(message)
    except ValueError:
        bot.send_message(message.chat.id, 'Invalid selection. Please choose a valid service.')
        start(message)


# View upcoming appointments
@bot.message_handler(func=lambda message: message.text.lower() == 'upcoming appointments', content_types=['text'])
def view_upcoming_appointments(message):
    user_id = message.from_user.id
    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM appointments WHERE user_id = ? AND date >= ? ORDER BY date, start_time',
                       (user_id, datetime.now().strftime('%Y-%m-%d')))
        appointments = cursor.fetchall()

    if not appointments:
        bot.send_message(message.chat.id, 'No upcoming appointments.')
        start(message)
        return

    table_headers = ['Date', 'Time', 'Service', 'Price']
    appointment_table = []
    for appointment in appointments:
        appointment_table.append([appointment[3], appointment[4], appointment[6], appointment[7]])
    html_table = tabulate.tabulate(appointment_table, table_headers, tablefmt='grid')
    appointments_message = f'Upcoming Appointments:\n <pre>{html_table}</pre>'
    bot.send_message(message.chat.id, appointments_message, parse_mode='HTML')

    start(message)


# Booking history
@bot.message_handler(func=lambda message: message.text.lower() == 'booking history', content_types=['text'])
def view_booking_history(message):
    user_id = message.from_user.id
    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM appointments WHERE user_id = ? ORDER BY date, start_time', (user_id,))
        appointments = cursor.fetchall()

    if not appointments:
        bot.send_message(message.chat.id, 'No booking history.')
        start(message)
        return

    table_headers = ['Date', 'Time', 'Service', 'Price']
    appointment_table = []
    for appointment in appointments:
        appointment_table.append([appointment[3], appointment[4], appointment[6], appointment[7]])
    html_table = tabulate.tabulate(appointment_table, table_headers, tablefmt='grid')
    history_message = f'Booking History:\n <pre>{html_table}</pre>'
    bot.send_message(message.chat.id, history_message, parse_mode='HTML')

    start(message)


# Cancel appointment
@bot.message_handler(func=lambda message: message.text.lower() == 'cancel appointment', content_types=['text'])
def choose_cancel(message):
    user_id = message.from_user.id
    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM appointments WHERE user_id = ? AND date >= ? ORDER BY id',
                       (user_id, datetime.now().strftime('%Y-%m-%d')))
        user_appointments = cursor.fetchall()
    appointment_ids_buttons = [
        telebot.types.KeyboardButton(str(i[0]))
        for i in user_appointments
    ]
    reply_markup = add_home_button(ReplyKeyboardMarkup(one_time_keyboard=True).add(*appointment_ids_buttons))

    table_headers = ['ID', 'Date', 'Time', 'Service']
    appointment_table = []
    for appointment in user_appointments:
        appointment_table.append([str(appointment[0]), appointment[3], appointment[4], appointment[6]])
    html_table = tabulate.tabulate(appointment_table, table_headers, tablefmt='grid')
    timetable_message = f'Please select an appointment to cancel\U0001FAE0 \nYour appointments: \n <pre>{html_table}</pre>'

    bot.send_message(message.chat.id, timetable_message, reply_markup=reply_markup, parse_mode='HTML')
    bot.register_next_step_handler(message, cancel_appointment)


def cancel_appointment(message):
    selected_appointment = str(message.text)
    if not selected_appointment:
        bot.send_message(message.chat.id, f'No appointment selected.')
        return start(message)

    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT date, start_time FROM appointments WHERE id = ? AND user_id = ?',
                       (selected_appointment, message.from_user.id))
        appointment = cursor.fetchone()

    if appointment:
        date_to_cancel, time_to_cancel = appointment
        msg = bot.send_message(message.chat.id,
                               f'Are you sure you want to cancel the appointment on {date_to_cancel} at {time_to_cancel}? Reply with "yes" to confirm.')
        bot.register_next_step_handler(msg, confirm_cancel_appointment, selected_appointment)
    else:
        bot.send_message(message.chat.id, 'You can only cancel your own appointments.')
        start(message)


def confirm_cancel_appointment(message, selected_appointment):
    if message.text.lower() == 'yes':
        with sqlite3.connect(db) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM appointments WHERE id = ? AND user_id = ?',
                           (selected_appointment, message.from_user.id))
            conn.commit()
        bot.send_message(message.chat.id,
                         f'Appointment #{selected_appointment} has been successfully cancelled! \U0000274C')
    else:
        bot.send_message(message.chat.id, 'Cancellation aborted.')
    start(message)


@bot.message_handler(func=lambda message: message.text.lower() == 'cancel unavailability', content_types=['text'])
def cancel_unavailability(message):
    if message.from_user.username != 'ordyaned':
        bot.send_message(message.chat.id, 'You do not have access to cancel unavailabilities.')
        return start(message)

    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM unavailabilities ORDER BY date, start_time')
        unavailabilities = cursor.fetchall()

    if not unavailabilities:
        bot.send_message(message.chat.id, 'No unavailabilities set.')
        return start(message)

    unavailability_buttons = [
        telebot.types.KeyboardButton(str(i[0]))
        for i in unavailabilities
    ]
    reply_markup = ReplyKeyboardMarkup(one_time_keyboard=True).add(*unavailability_buttons)

    table_headers = ['ID', 'Date', 'Start Time', 'End Time']
    unavailability_table = []
    for unavailability in unavailabilities:
        unavailability_table.append([str(unavailability[0]), unavailability[1], unavailability[2], unavailability[3]])
    html_table = tabulate.tabulate(unavailability_table, table_headers, tablefmt='grid')
    unavailability_message = f'Select an unavailability to cancel:\n <pre>{html_table}</pre>'
    bot.send_message(message.chat.id, unavailability_message, reply_markup=reply_markup, parse_mode='HTML')
    bot.register_next_step_handler(message, confirm_cancel_unavailability)


def confirm_cancel_unavailability(message):
    selected_unavailability = str(message.text)
    if not selected_unavailability:
        bot.send_message(message.chat.id, 'No unavailability selected.')
        return start(message)

    msg = bot.send_message(message.chat.id,
                           f'Are you sure you want to cancel the unavailability #{selected_unavailability}? Reply with "yes" to confirm.')
    bot.register_next_step_handler(msg, finalize_cancel_unavailability, selected_unavailability)


def finalize_cancel_unavailability(message, selected_unavailability):
    if message.text.lower() == 'yes':
        with sqlite3.connect(db) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM unavailabilities WHERE id = ?', (selected_unavailability,))
            conn.commit()
        bot.send_message(message.chat.id,
                         f'Unavailability #{selected_unavailability} has been successfully cancelled! \U0000274C')
    else:
        bot.send_message(message.chat.id, 'Cancellation aborted.')
    start(message)


@bot.message_handler(commands=['cleanup'])
def cleanup_whole_database(message):
    if message.from_user.username != 'ordyaned':
        bot.send_message(message.chat.id, 'Unauthorized action.')
        start(message)
        return

    else:
        with sqlite3.connect(db) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM appointments')
            cursor.execute('DELETE FROM unavailabilities')
            conn.commit()
        bot.send_message(message.chat.id, 'Database successfully cleaned up.')


if __name__ == '__main__':
    bot.polling(none_stop=True)