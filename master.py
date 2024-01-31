import os
import sqlite3
import telebot
import tabulate
from datetime import datetime, timedelta
from telebot.types import ReplyKeyboardMarkup

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

db = os.getenv('DB_PATH')

# Conversation states
MENU, DATE, TIME = range(3)


@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    item_reserve = telebot.types.KeyboardButton('Reserve')
    item_timetable = telebot.types.KeyboardButton('Timetable')
    item_cancel = telebot.types.KeyboardButton('Cancel Reservation')
    markup.add(item_reserve, item_timetable, item_cancel)

    bot.send_message(message.chat.id, 'Welcome to the CiUP Washing Machine Reservation Bot! \U0001F917 \U0001F9FA \nPlease '
                                      'choose an option below:', reply_markup=markup)


def menu(message):
    user_choice = message.text.lower()

    if user_choice == 'reserve':
        reserve_start(message)
    elif user_choice == 'timetable':
        show_timetable(message)
    elif user_choice == 'cancel reservation':
        choose_cancel(message)
    else:
        bot.send_message(message.chat.id, 'Invalid choice. \U0001F468 \n Please choose either "Reserve", "Timetable" '
                                          'or "Cancel' 'Reservation"')
        bot.register_next_step_handler(message, start)


def get_time_slots(working_day: bool) -> list:
    if working_day:
        return [(f'{i:02d}:00', (datetime.strptime(f'{i:02d}:00', '%H:%M') + timedelta(hours=1)).strftime('%H:%M')) for
                i in range(18, 24)]
    else:
        return [(f'{i:02d}:00', (datetime.strptime(f'{i:02d}:00', '%H:%M') + timedelta(minutes=90)).strftime('%H:%M'))
                for i in range(10, 24)]


@bot.message_handler(func=lambda message: message.text.lower() == 'reserve', content_types=['text'])
def reserve_start(message):
    try:
        date_buttons = [
            telebot.types.KeyboardButton((datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d'))
            for i in range(7)
        ]
        reply_markup = ReplyKeyboardMarkup(one_time_keyboard=True).add(*date_buttons)
        bot.send_message(message.chat.id, '\U0001F4C5 Please select a date for the reservation: \U0001F4C5', reply_markup=reply_markup)
        bot.register_next_step_handler(message, reserve_date)
    except ValueError:
        bot.send_message(message.chat.id, 'Invalid date format. Please use the format YYYY-MM-DD to select a date for the reservation.')
        start(message)

def reserve_date(message):
    try:
        selected_date = message.text

        # Determine if the selected date is a working day (Monday to Friday)
        is_working_day = datetime.strptime(selected_date, '%Y-%m-%d').weekday() < 5

        # Get time slots based on the type of day
        time_slots = get_time_slots(is_working_day)

        # Create a custom keyboard with time slots
        time_buttons = [
            telebot.types.KeyboardButton(f'{start} - {end}')
            for start, end in time_slots
        ]

        reply_markup = ReplyKeyboardMarkup(one_time_keyboard=True).add(*time_buttons)
        bot.send_message(message.chat.id, '\U0001F55C Please select a time for the reservation: \U0001F55C', reply_markup=reply_markup)

        # Save the selected date in the conversation context
        bot.register_next_step_handler(message, reserve_time, selected_date)
    except ValueError:
        bot.send_message(message.chat.id, 'Invalid date format. Please use the format YYYY-MM-DD to select a date for the reservation.')
        start(message)


def reserve_time(message, selected_date):
    try:
        user_id = message.from_user.id
        username = str(message.from_user.first_name) + ' ' + str(message.from_user.last_name)
        date = selected_date

        # Split the selected time string into start and end times
        start_time, end_time = message.text.split(' - ')

        # Convert start and end times to datetime objects
        start_time_dt = datetime.strptime(start_time, '%H:%M')
        end_time_dt = datetime.strptime(end_time, '%H:%M')

        # Check if the selected time is within the allowed time frame
        selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d')

        if selected_date_obj.weekday() < 5:  # Weekdays (Monday to Friday)
            allowed_start_time = datetime.strptime('18:00', '%H:%M')
            allowed_end_time = datetime.strptime('23:59', '%H:%M')
            slot_duration = timedelta(hours=1)
        else:  # Weekends (Saturday and Sunday)
            allowed_start_time = datetime.strptime('10:00', '%H:%M')
            allowed_end_time = datetime.strptime('23:59', '%H:%M')
            slot_duration = timedelta(minutes=90)

        # Check if the selected time is within the allowed time frame
        if not allowed_start_time <= start_time_dt < allowed_end_time:
            bot.send_message(message.chat.id, 'Invalid time. \U0001F468 \n'
                                          'Reservations are only allowed between {} and {}.\U0001F557'.format(
                allowed_start_time.strftime('%H:%M'), allowed_end_time.strftime('%H:%M')))
            start(message)
            return

        # Check if the selected time slot is available
        with sqlite3.connect(db) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM reservations WHERE date = ? AND start_time = ?', (date, start_time))
            existing_reservation = cursor.fetchone()

        if existing_reservation:
            bot.send_message(message.chat.id,
                             f'The selected time slot is already reserved by {existing_reservation[2]}. \n'
                             f'Please choose another time. \U0001F55D')
            start(message)
            return

        # Save the reservation in the database
        with sqlite3.connect(db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO reservations (user_id, username, date, start_time, end_time) VALUES (?, ?, ?, ?, ?)',
                (user_id, username, date, start_time, end_time))
            conn.commit()

        bot.send_message(message.chat.id,
                         f'Reservation successful! \U0001F604 \U00002705 \U0001F490 \n'
                         f'You have reserved the washing machine for \n{date} from {start_time} to {end_time}.')

        start(message)
    except ValueError:
        bot.send_message(message.chat.id, 'Invalid time format. Please select a valid time for the reservation.')
        start(message)

        
@bot.message_handler(func=lambda message: message.text.lower() == 'timetable', content_types=['text'])
def show_timetable(message):
    user_id = message.from_user.id
    date_buttons = [
        telebot.types.KeyboardButton((datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d'))
        for i in range(7)
    ]
    reply_markup = ReplyKeyboardMarkup(one_time_keyboard=True).add(*date_buttons)
    bot.send_message(message.chat.id, '\U0001F4C5 Please select a date for the reservation: \U0001F4C5', reply_markup=reply_markup)
    bot.register_next_step_handler(message, retrieve_timetable)


def retrieve_timetable(message):
    selected_date = message.text

    if not selected_date:
        bot.send_message(message.chat.id, '\U0001F4C5 Please select a date first using /reserve command.')
        start(message)
        return

    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM reservations WHERE date = ? ORDER BY date, start_time', (selected_date,))
        reservations = cursor.fetchall()

    if not reservations:
        bot.send_message(message.chat.id, f'No reservations for {selected_date}.')
        start(message)
        return

    table_headers = ['ID', 'Username', 'Time']
    reservation_table = []
    for reservation in reservations:
        reservation_table.append([str(reservation[0]), reservation[2], reservation[4]])
    html_table = tabulate.tabulate(reservation_table, table_headers, tablefmt='grid')
    timetable_message = f'Reservations for {selected_date}:\n <pre>{html_table}</pre>'
    bot.send_message(message.chat.id, timetable_message, parse_mode='HTML')

    start(message)


@bot.message_handler(func=lambda message: message.text.lower() == 'cancel reservation', content_types=['text'])
def choose_cancel(message):
    user_id = message.from_user.id
    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM reservations WHERE user_id = ? ORDER BY id', (user_id,))
        user_reservations = cursor.fetchall()
    reservation_ids_buttons = [
        telebot.types.KeyboardButton(i[0])
        for i in user_reservations
    ]
    reply_markup = ReplyKeyboardMarkup(one_time_keyboard=True).add(*reservation_ids_buttons)

    table_headers = ['ID', 'Date', 'Time']
    reservation_table = []
    for reservation in user_reservations:
        reservation_table.append([str(reservation[0]), reservation[3], reservation[4]])
    html_table = tabulate.tabulate(reservation_table, table_headers, tablefmt='grid')
    timetable_message = f'Please select a reservation to cancel\U0001FAE0 \nYour reservations: \n <pre>{html_table}</pre>'

    bot.send_message(message.chat.id, timetable_message, reply_markup=reply_markup, parse_mode='HTML')
    bot.register_next_step_handler(message, cancel_reservation)


def cancel_reservation(message):
    selected_reservation = str(message.text)
    if not selected_reservation:
        bot.send_message(message.chat.id, f'No reservation selected.')
        start(message)
        return
    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM reservations WHERE id = ?', (selected_reservation,))
        bot.send_message(message.chat.id, f'Reservation #{selected_reservation} has been successfully cancelled! \U0000274C')
        start(message)
        return


@bot.message_handler(commands=['cleanup'])
def cleanup_whole_database(message):
    if message.from_user.username != 'ordyaned':
        bot.send_message(message.chat.id, 'Please stop playing')
        start(message)
        return

    else:
        with sqlite3.connect(db) as conn:
            cursor = conn.cursor()

            cursor.execute('DELETE FROM reservations')
            conn.commit()
        bot.send_message(message.chat.id, 'DB successfully cleaned up')


if __name__ == '__main__':
    bot.polling(none_stop=True)

