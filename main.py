import logging

import telegram
from telegram import (Update, Message, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply)
from telegram.ext import (Updater, MessageHandler, CommandHandler, ConversationHandler, Filters, CallbackQueryHandler)

import os 

from model import (Activity, init_db, get_activities_by_user_id, get_activity_by_id, delete_activity_by_id, get_leaderboard_activities,
                    Leaderboard, get_leaderboard_by_id, leaderboard_has_activities, get_leaderboard_by_activity_id,
                    User, get_user_by_id, get_leaderboard_score, get_performed_activities, get_performed_activity_by_id,
                    Participant, get_participant_by_user_id_and_leaderboard_id,get_leaderboard_log, 
                    Performed_Activity)
import gcloud


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)

# State variables
ACTIVITY, POINTS, IDLE, DELETE, EXECUTE_ACTIVITY, CANCEL  = range(6) 

# Variables for start flow 
EXECUTE, TO_ADD, TO_DELETE, SCORE, LOG, CANCEL = range(6)


#TODO: 
# - Fix format of log on mobile
# - Fix: Force_reply is sent to all users 
# - Fix: if inline keyboard is clicked by user who not triggered command, 
#  -- keyboard is removed but command is not recorded 
#  -- incorrect button ID is recorded 
 
# All activities should be added to the bot via @botfather /setcommands
# Available commands:
# start - Enter chat's Leaderboard
# execute_activity - Record Activity Execution
# cancel_activity - Cancel Executed Activity
# show_score - Show current score 
# add_activity - Add new Activity
# delete_activity - Delete Activity
# show_activities - Show Leaderboard's Activityes 
# show_log - Show last 10 Executed Activities
# cancel - End interaction with the bot



def start(update: Update, context):

    update.message.reply_text(
        'Ok, let\'s start'
    )

    # Create Leaderboard if do not exists 
    leaderboard = create_leaderboard(update, context)
    # Create/Update User 
    user = create_user(update, context)
    # Add user to the Leaderboard
    add_participant(update, user, leaderboard)

    # Get leaderboard activities 
    acitivity_exists = leaderboard_has_activities(leaderboard_id = leaderboard.id)

    if not acitivity_exists:
        # Telegram clients will display a reply interface to the user 
        # (act as if the user has selected the bot’s message and tapped ‘Reply’) 
        force_reply = ForceReply(force_reply=True)
        update.message.reply_text(
            'Seems there is no Activities. \nSend me the name of a first activity',
            reply_markup=force_reply,
            quote = False
        )
        return ACTIVITY
    else: 
        return wait_for_input(update, context)


def create_leaderboard(update:Update, context):
    """
    Create Leaderboard if do not exists 
    Update Leaderboard if exists
    """
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type

    if chat_type == 'private':
        leaderboard_name = update.effective_chat.username
    else: 
        leaderboard_name = update.effective_chat.title

    leaderboard = get_leaderboard_by_id(leaderboard_id=chat_id)
    

    #If leaderboard is not present - create new
    if not leaderboard:
        leaderboard = Leaderboard(id=chat_id, name=leaderboard_name)
    else:
        #Update Leaderboard name, in case Chat name was updated
        leaderboard.name = leaderboard_name
    leaderboard.save_leaderboard()

    return leaderboard

def create_user(update:Update, context):
    """
    Check if User is db, create if not, update is yes
    """
    user_id = update.effective_user.id
    user_name = update.effective_user.username
    user = get_user_by_id(id=user_id)

    if not user:
        user = User(name=user_name, id=user_id)
    else:
        #Adding this check because user can change the name
        user.name = user_name
    user.save_user()
    return user

def add_participant(update:Update, user:User, leaderboard:Leaderboard):
    """
    Add Participant to db if not present
    """
    chat_type = update.effective_chat.type
    participant = get_participant_by_user_id_and_leaderboard_id(user_id = user.id, leaderboard_id=leaderboard.id)

    if not participant: 
        participant = Participant(user_id = user.id, leaderboard_id=leaderboard.id)
        participant.save_participant()

        #If group chat - notify participants that new participant was added 
        if chat_type != 'private':
            update.message.reply_text(
                f'{user.name} was added to the Leaderboard {leaderboard.name}', 
                quote=False
            )
    return participant   



#/add_activity command handler
def add_activity_command_handler(update:Update, context):
    #If command was triggered from inline keyboard submit
    query = update
    if update.callback_query:
        query = update.callback_query
        query.answer()

    force_reply = ForceReply(force_reply=True)
    query.message.reply_text(
        f'What is the name of the Activity?', 
        reply_markup=force_reply,
        quote = False
    )
    return ACTIVITY

#TODO: Add check if activity with same name.lower() exists
def add_activity(update: Update, context):
    activity = update.message.text
    if not activity:
        force_reply = ForceReply(force_reply=True)
        update.message.reply_text(
            f'Only text is allowed as a name of the Activity', 
            reply_markup=force_reply,
            quote = False
        )
        return add_activity_command_handler(update, context)

    context.user_data[ACTIVITY] = activity

    # Telegram clients will display a reply interface to the user 
    # (act as if the user has selected the bot’s message and tapped ‘Reply’) 
    force_reply = ForceReply(force_reply=True)
    update.message.reply_text(
        f'How many points should I assign for {context.user_data[ACTIVITY]}?', 
        reply_markup=force_reply,
        quote = False
    )

    return POINTS


def add_points(update: Update, context):
    points = update.message.text
    try:
        int(points) 
    except:
        # Telegram clients will display a reply interface to the user 
        # (act as if the user has selected the bot’s message and tapped ‘Reply’) 
        force_reply = ForceReply(force_reply=True, selective=True)
        update.message.reply_text(
            f'{points} is not a number. Please enter number 😊', 
            reply_markup=force_reply
        )
        return POINTS
    else:

        context.user_data[POINTS] = points
        update.message.reply_text(
            f'Ok. Activity {context.user_data[ACTIVITY]} gives {context.user_data[POINTS]} points 😎', 
            quote = False
        )

        # Saving activity to the database
        act = Activity(activity_name=context.user_data[ACTIVITY], points=context.user_data[POINTS], author_user_id=update.effective_user.id, leaderboard_id =update.effective_chat.id  )
        act.save_activity()

        # Get new user input
        return wait_for_input(update, context)

def wait_for_input(update:Update, context):
    
    #TODO: Add Stop Button
    # Add Show Activities button
    # Add record Activity button 
    keyboard = [
        [InlineKeyboardButton("✅ Execute Activity", callback_data=EXECUTE)],
        [InlineKeyboardButton("➕ Add Activity", callback_data=TO_ADD),InlineKeyboardButton("➖ Delete Activity", callback_data=TO_DELETE)],
        [InlineKeyboardButton("🏅 Show Score", callback_data=SCORE),InlineKeyboardButton("📝 Show Log", callback_data=LOG)], 
        [InlineKeyboardButton("🛑 End", callback_data=CANCEL)]
    ]

    keyboard_markup = InlineKeyboardMarkup(keyboard)

    # Send update to the user
    # Check if user entered any update
    message_text = f'What would you like to do? 😏'
    if update.message:
        update.message.reply_text(
            message_text, reply_markup = keyboard_markup, 
            quote = False
        )
    # Check if user clicked inline button
    else:
        query = update.callback_query
        query.answer()
        query.message.reply_text(
            message_text, reply_markup = keyboard_markup,
            quote = False
        )

     
    return IDLE


def idle(update:Update, context):
    
    query = update.callback_query
    query.answer()

    #User choice
    choice = int(query.data)


    #Remove InLineKeyboard
    query.edit_message_text(
        query.message.text
    )

    if choice == EXECUTE:
        query.message.reply_text(
            query.message.reply_markup.inline_keyboard[0][0].text, 
            quote=False
        )
        return execute_activity_command_handler(update, context)
    elif choice == TO_ADD:
        query.message.reply_text(
            query.message.reply_markup.inline_keyboard[1][0].text,
            quote = False
        )
        return add_activity_command_handler(update, context)
    elif choice == TO_DELETE: 
        query.message.reply_text(
            query.message.reply_markup.inline_keyboard[1][1].text,
            quote = False
        )
        return delete_command_handler(update, context)
    elif choice == SCORE:
        query.message.reply_text(
            query.message.reply_markup.inline_keyboard[2][0].text,
            quote = False
        )
        return show_score_command_handler(update, context)
    elif choice == LOG:
        query.message.reply_text(
            query.message.reply_markup.inline_keyboard[2][1].text,
            quote = False
        )
        return show_log_command_handler(update, context)
    elif choice == CANCEL:
        query.message.reply_text(
            query.message.reply_markup.inline_keyboard[3][0].text,
            quote = False
        )
        return cancel(update, context)

# /execute_activity command handler
def execute_activity_command_handler(update:Update, context):
    #If command was triggered from inline keyboard submit
    query = update
    if update.callback_query:
        query = update.callback_query
        query.answer()

    
    # Get leaderboard activities 
    leaderboard_id = update.effective_chat.id
    activities = get_leaderboard_activities(leaderboard_id = leaderboard_id)

    if activities.count() < 1:
        # Telegram clients will display a reply interface to the user 
        # (act as if the user has selected the bot’s message and tapped ‘Reply’) 
        force_reply = ForceReply(force_reply=True, selective=True)
        query.message.reply_text(
            'Seems there is no Activities. \nSend me the name of a first activity',
            reply_markup=force_reply,
            quote = False
        )
        return ACTIVITY
    else: 
        keyboard = []
        for i, act in enumerate(activities):
            # Need this to understand what button was clicked
            data_ = f'{i}_{act.id}_{act.activity_name}_{act.points}'
            key = [InlineKeyboardButton(f'{act.activity_name} - {act.points} points', callback_data=data_)]
            keyboard.append(key)
        
        key = [InlineKeyboardButton(f'❌ Cancel', callback_data=f"{activities.count()}_{-1}")]
        keyboard.append(key)

        keyboard_markup = InlineKeyboardMarkup(keyboard)
        
        query.message.reply_text(
            f'What Acitivity you would like to record?', reply_markup=keyboard_markup,
            quote = False
        )
        return EXECUTE_ACTIVITY

def execute_activity(update:Update, context):
    query = update.callback_query
    query.answer()

    button_id, activity_id, activity_name, points = query.data.split('_')
    activity_id = int(activity_id)
    button_id = int(button_id)

    #Remove Inline Keyboard
    query.edit_message_reply_markup(
        None, 
        quote = False
    )
    #Send user choise as a message
    query.message.reply_text(
        query.message.reply_markup.inline_keyboard[button_id][0].text, 
        quote=False
    ) 

    #Return to user input in case Calcel is clicked
    if activity_id == -1:
        return wait_for_input(update, context)
    
    user_id = update.effective_user.id
    leaderboard_id = update.effective_chat.id
    participant = get_participant_by_user_id_and_leaderboard_id(user_id = user_id,
                                                                 leaderboard_id = leaderboard_id)
    if not participant: 
        participant = Participant(user_id = user_id, leaderboard_id = leaderboard_id)
        participant.save_participant()


    # Create performed Activity
    performed_activity = Performed_Activity(activity_id = activity_id, participant_id = participant.id)    
    performed_activity.save_performed_activity()

    query.message.reply_text(
            f'Activity {activity_name} was tracked\n'
            f'{points} points were added to @{update.effective_user.username}', 
            quote=False
        )
    return ConversationHandler.END

# Handles /delete_activity command
def delete_command_handler(update:Update, context):
    
    #If command was triggered from inline keyboard submit
    query = update
    if update.callback_query:
        query = update.callback_query
        query.answer()

    # Get leaderboard activities 
    activities = get_leaderboard_activities(leaderboard_id = update.effective_chat.id)

    # If there is no activities return to default
    if activities.count() < 1:
        query.message.reply_text(
            f'✋ There are no activities 😐',
            quote = False
        )
        return wait_for_input(update, context)
    else:
        keyboard = []
        #TODO: Add Cancel button. Should abort deletion of the activity. 
        # Should end interaction with bot 
        for indx, act in enumerate(activities):
            key = [InlineKeyboardButton(f'{act.activity_name} - {act.points} points', callback_data=f"{indx}_{act.id}")]
            keyboard.append(key)
        
        key = [InlineKeyboardButton(f'❌ Cancel', callback_data=f"{activities.count()}_{-1}")]
        keyboard.append(key)

        keyboard_markup = InlineKeyboardMarkup(keyboard)
        
        query.message.reply_text(
            f'What Acitivity you would like to delete?', reply_markup=keyboard_markup,
            quote = False
        )

        return DELETE


#TODO: Check if any Performed_Activity entities exists. If Yes ask for confirmation 
def delete(update:Update, context):
    query = update.callback_query
    query.answer()

    button_id, activity_id = query.data.split('_')
    activity_id = int(activity_id)
    button_id = int(button_id)

    #Remove Inline Keyboard
    query.edit_message_reply_markup(
        None
    )

    query.message.reply_text(
            query.message.reply_markup.inline_keyboard[button_id][0].text, 
            quote = False
        )

    if activity_id == -1:
        return wait_for_input(update, context)

    #Delete activity from the database
    activity = get_activity_by_id(activity_id=activity_id)
    activity.delete_activity()


    query.message.reply_text(
            f'Activity {activity.activity_name} was deleted ❌',
            quote = False
        )
    
    # Get new user input
    return ConversationHandler.END


def cancel(update:Update, context):
    #If command was triggered from inline keyboard submit
    query = update
    if update.callback_query:
        query = update.callback_query
        query.answer()

    query.message.reply_text(
        f'Ok. Bye 👋🏽',
        quote = False
    )
    return ConversationHandler.END 

# /show_score - Shows Leaderboard score 
def show_score_command_handler(update:Update, context):

    #If command was triggered from inline keyboard submit
    query = update
    if update.callback_query:
        query = update.callback_query
        query.answer()

    chat_id = update.effective_chat.id
    
    score = get_leaderboard_score(leaderboard_id = chat_id)
    score_message = ''
    if score:
        for indx, row in enumerate(score):
            score_message+= f"{'🥇 ' if indx == 0 else ''}" + f"{row['name']}" +' - '+ f"{row['points']}" + '💎\n  '
        query.message.reply_text(
            score_message,
            quote = False
        )
    else:
        query.message.reply_text(
            f'Leaderboard has not started. Send /start to enter the Leaderboard🏆'
        )

    return ConversationHandler.END 

# /show_activities - Shows Leaderboard's Activityes 
def show_activities_command_handler(update:Update, context):

    leaderboard_id = update.effective_chat.id
    # Get leaderboard activities 
    activities = get_leaderboard_activities(leaderboard_id = leaderboard_id)
    
    if activities.count() < 1:
        # Telegram clients will display a reply interface to the user 
        # (act as if the user has selected the bot’s message and tapped ‘Reply’) 
        
        update.message.reply_text(
            'Seems there is no Activities. \n'
            'Send /start or /add_activity command to add first activity'
        )
    else:
        message = f"There {'is' if activities.count() == 1 else 'are'} {activities.count()} Activit{'y' if activities.count() == 1 else 'ies'}:\n"
        for indx, act in enumerate(activities):
            message += f'{indx+1}. {act.activity_name} ➖ {act.points} 💎\n'
        update.message.reply_text(
            message 
        )
    return ConversationHandler.END

# /show_log - Show last 10 Executed Activities
def show_log_command_handler(update:Update, context):
    #If command was triggered from inline keyboard submit
    query = update
    if update.callback_query:
        query = update.callback_query
        query.answer()

    leaderboard_id = update.effective_chat.id

    log = get_leaderboard_log(leaderboard_id = leaderboard_id, count = 10)

    message = ''
    if log.rowcount > 0: 
        for row in log: 
            message += f"{row['name']} - {row['activity_name']} -- {row['points']}💎 -- {row['time_created']:%m-%d %H:%M}\n"
    else: 
        message = 'No Activities Performed yet 🤷🏻'

    query.message.reply_text(message, quote = False)

    return ConversationHandler.END

#TODO: Implement cancel command
def cancel_activity_command_handler(update:Update, context):
    
    #If command was triggered from inline keyboard submit
    query = update
    if update.callback_query:
        query = update.callback_query
        query.answer()

    user_id = update.effective_user.id
    leaderboard_id = update.effective_chat.id

    activities = get_performed_activities(user_id = user_id, leaderboard_id = leaderboard_id)
    
    message = ''
    if activities.rowcount > 0:
        keyboard = []
        #TODO: Add Cancel button. Should abort deletion of the activity. 
        # Should end interaction with bot 
        for indx, act in enumerate(activities):
            key = [InlineKeyboardButton(f"{act['name']} - {act['time']:%m-%d %H:%M}", callback_data=f"{indx}_{act['id']}")]
            keyboard.append(key)
        
        key = [InlineKeyboardButton(f'❌ Cancel', callback_data=f"{activities.rowcount}_{-1}")]
        keyboard.append(key)

        keyboard_markup = InlineKeyboardMarkup(keyboard)
        
        query.message.reply_text(
            f'What Acitivity you would like to cancel?', reply_markup=keyboard_markup,
            quote = False
        )
        return CANCEL

    else:
        message = 'You have no executed activities yet 🤷🏻'
        query.message.reply_text(message, quote = False)
        return ConversationHandler.END


def cancel_activity(update: Update, context):
    query = update.callback_query
    query.answer()

    button_id, performed_activity_id = query.data.split('_')
    performed_activity_id = int(performed_activity_id)
    button_id = int(button_id)

    #Remove Inline Keyboard
    query.edit_message_reply_markup(
        None
    )

    query.message.reply_text(
            query.message.reply_markup.inline_keyboard[button_id][0].text, 
            quote = False
        )

    if performed_activity_id == -1:
        return cancel(update, context)

    #Delete performed activity from the database
    performed_activity = get_performed_activity_by_id(id=performed_activity_id)
    activity = get_activity_by_id(activity_id=performed_activity.activity_id)
    performed_activity.delete_performed_activity()


    query.message.reply_text(
            f"{activity.activity_name} - {performed_activity.time_created:%m-%d %H:%M} was canceled ❌",
            quote = False
        )
    
    # Get new user input
    return ConversationHandler.END




def main():

    env = os.environ.get('ENV')
    webhook_url = os.environ.get('WEBHOOK_URL')
    port = os.environ.get('PORT_T')
    mode = os.environ.get('MODE')

    if env == "GCLOUD":
        project_id = os.environ.get('GCLOUD_PROJECT_ID')
        logging.info(os.environ.get('GCLOUD_PROJECT_ID'))

        gcl = gcloud.Gcloud(project_id)
        token = gcl.access_secret_version()
    else:
        token = os.environ.get("TOKEN")

    #Create Updater
    updater = Updater(token=token, use_context=True)
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start),
                     CommandHandler('add_activity', add_activity_command_handler), 
                     CommandHandler('execute_activity', execute_activity_command_handler), 
                     CommandHandler('show_score', show_score_command_handler), 
                     CommandHandler('show_activities', show_activities_command_handler),
                     CommandHandler('show_log', show_log_command_handler), 
                     CommandHandler('delete_activity',delete_command_handler),
                     CommandHandler('cancel_activity',cancel_activity_command_handler)], 
        states = {
            ACTIVITY : [ MessageHandler(Filters.all, add_activity, pass_user_data=True)],
            POINTS : [MessageHandler(Filters.all, add_points, pass_user_data=True)], 
            IDLE : [CallbackQueryHandler(idle,  pass_user_data=True)], 
            DELETE : [CallbackQueryHandler(delete, pass_user_data=True)],
            EXECUTE_ACTIVITY : [CallbackQueryHandler(execute_activity, pass_user_data=True)], 
            CANCEL: [CallbackQueryHandler(cancel_activity, pass_user_data=True)]
        }, 
        fallbacks=[CommandHandler('start', start), 
                 CommandHandler('execute_activity', execute_activity_command_handler), 
                 CommandHandler('add_activity', add_activity_command_handler), 
                 CommandHandler('show_score', show_score_command_handler), 
                 CommandHandler('show_activities', show_activities_command_handler), 
                 CommandHandler('show_log', show_log_command_handler), 
                 CommandHandler('cancel', cancel),
                 CommandHandler('delete_activity',delete_command_handler),
                 CommandHandler('cancel_activity',cancel_activity_command_handler)]
    )
    
    #Create Dispatcher
    disp = updater.dispatcher

    #Add handlers to updater
    disp.add_handler(conv_handler)

    #Init database
    init_db() 

    if mode == 'webhook':
        #Start polling from Telegram
        updater.start_webhook(listen='0.0.0.0',
                        port=port,
                        url_path=token)
    else: 
        updater.start_polling()

    updater.idle()




if __name__ == "__main__":
    main() 





