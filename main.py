import logging

import telegram
from telegram import (Update, Message, InlineKeyboardButton, InlineKeyboardMarkup, ForceReply)
from telegram.ext import (Updater, MessageHandler, CommandHandler, ConversationHandler, Filters, CallbackQueryHandler)

import os 

from model import (Activity, init_db, get_activities_by_user_id, get_activity_by_id, delete_activity_by_id, get_leaderboard_activities,
                    Leaderboard, get_leaderboard_by_id, leaderboard_has_activities, get_leaderboard_by_activity_id,
                    User, get_user_by_id, get_leaderboard_score,
                    Participant, get_participant_by_user_id_and_leaderboard_id,
                    Performed_Activity)
import gcloud


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)

ACTIVITY, POINTS, IDLE, DELETE, EXECUTE_ACTIVITY  = range(5) 


#TODO: Implement commands
# All activities should be added to the bot via @botfather /setcommands
#
# 
# /delete_activity - Delete Activity
# /cancel - End interaction with the bot
# /show_log - Show last 10 Executed Activities
 
# All activities should be added to the bot via @botfather /setcommands
# Available commands:
# /start - Enter chat's Leaderboard
# /add_activity - Add new Activity
# /execute_activity - Record Activity Execution 
# /show_score - Show current score 
# /show_activities - Show Leaderboard's Activityes 


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
        force_reply = ForceReply(force_reply=True, selective=True)
        update.message.reply_text(
            'Seems there is no Activities. \nSend me the name of a first activity',
            reply_markup=force_reply
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


#TODO: Add check if activity with same name.lower() exists
def add_activity(update: Update, context):
    activity = update.message.text
    context.user_data[ACTIVITY] = activity
    update.message.reply_text(
        f'Ok. Activity {context.user_data[ACTIVITY]} added',
        quote = True
    )

    # Telegram clients will display a reply interface to the user 
    # (act as if the user has selected the bot’s message and tapped ‘Reply’) 
    force_reply = ForceReply(force_reply=True, selective=True)
    update.message.reply_text(
        f'How many points should I assign for {context.user_data[ACTIVITY]}?', 
        reply_markup=force_reply,
    )

    return POINTS

#/add_activity command handler
def add_activity_command_handler(update:Update, context):
    force_reply = ForceReply(force_reply=True, selective=True)
    update.message.reply_text(
        f'What is the name of the Activity?', 
        reply_markup=force_reply,
    )
    return ACTIVITY

# /execute_activity command handler
def execute_activity_command_handler(update:Update, context):
    # Create Leaderboard if do not exists 
    leaderboard = create_leaderboard(update, context)
    # Create/Update User 
    user = create_user(update, context)
    # Add user to the Leaderboard
    add_participant(update, user, leaderboard)
    
    # Get leaderboard activities 
    activities = get_leaderboard_activities(leaderboard_id = leaderboard.id)

    if activities.count() < 1:
        # Telegram clients will display a reply interface to the user 
        # (act as if the user has selected the bot’s message and tapped ‘Reply’) 
        force_reply = ForceReply(force_reply=True, selective=True)
        update.message.reply_text(
            'Seems there is no Activities. \nSend me the name of a first activity',
            reply_markup=force_reply
        )
        return ACTIVITY
    else: 
        keyboard = []
        for i, act in enumerate(activities):
            # Need this to understand what button was clicked
            data_ = f'{i}_{act.id}'
            key = [InlineKeyboardButton(f'{act.activity_name} - {act.points} points', callback_data=data_)]
            keyboard.append(key)
        
        keyboard_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            f'What Acitivity you would like to record?', reply_markup=keyboard_markup
        )
        return EXECUTE_ACTIVITY

def execute_activity(update:Update, context):
    query = update.callback_query
    query.answer()

    button_id, activity_id = query.data.split('_')
    activity_id = int(activity_id)
    button_id = int(button_id)

    #Remove Inline Keyboard
    query.edit_message_reply_markup(
        None
    )
    #Send user choise as a message
    query.message.reply_text(
        query.message.reply_markup.inline_keyboard[button_id][0].text, 
        quote=False
    ) 

    #Get activity 
    activity = get_activity_by_id(activity_id=activity_id)
    leaderboard = get_leaderboard_by_activity_id(activity_id=activity_id)
    #Record execution of the activity. Create Performed_Activity 

    # Create/Update User 
    user = create_user(update, context)
    # Add user to the Leaderboard == Create Participant 
    # Might be redundant but more robust :D 
    participant = add_participant(update, user, leaderboard)

    # Create performed Activity
    performed_activity = Performed_Activity(activity_id = activity.id, participant_id = participant.id)    
    performed_activity.save_performed_activity()

    query.message.reply_text(
            f'Activity {activity.activity_name} was tracked\n'
            f'{activity.points} points were added to {user.name}', 
            quote=False
        )
    return ConversationHandler.END


def add_points(update: Update, context):
    points = update.message.text
    try:
        int(points) 
    except ValueError:
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
        [InlineKeyboardButton("➕ Add Activity", callback_data=0)], 
        [InlineKeyboardButton("➖ Delete Activity", callback_data=1)]
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
            message_text, reply_markup = keyboard_markup
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
    #Send user choise as a message
    query.message.reply_text(
        query.message.reply_markup.inline_keyboard[choice][0].text
    ) 

    if choice == 0:
        # Telegram clients will display a reply interface to the user 
        # (act as if the user has selected the bot’s message and tapped ‘Reply’)
        # TODO: Figure out how to do selective force_reply. Some how set message.id to inline button id?
        # Alternatevly set selective=false
        force_reply = ForceReply(force_reply=True, selective=True)
        query.message.reply_text(
            f'Ok, send me the name of the Activity?', 
            reply_markup=force_reply
        )
        return ACTIVITY
    #TODO: Change to the Leaderboard activities
    elif choice == 1: 
        # Reading all user activities from the database 
        # And displaying it as a list of InlineKeyboardButtons
        activities = get_activities_by_user_id(user_id = update.effective_user.id )

        # If there is no activities return to default
        if activities.count() < 1:
            query.message.reply_text(
                f'✋ There are no activities left 😐'
            )
            return wait_for_input(update, context)


        keyboard = []
        #TODO: Add Cancel button. Should abort deletion of the activity. 
        # Should end interaction with bot 
        for act in activities:
            key = [InlineKeyboardButton(f'{act.activity_name} - {act.points} points', callback_data=act.id)]
            keyboard.append(key)
        
        keyboard_markup = InlineKeyboardMarkup(keyboard)
        
        query.message.reply_text(
            f'What Acitivity you would like to delete?', reply_markup=keyboard_markup
        )

        return DELETE

#TODO: Check if any Performed_Activity entities exists. If Yes ask for confirmation 
def delete(update:Update, context):
    query = update.callback_query
    query.answer()

    activity_id = int(query.data)

    #Delete activity from the database
    activity = get_activity_by_id(activity_id=activity_id)
    activity.delete_activity()

    #Remove Inline Keyboard
    query.edit_message_reply_markup(
        None
    )
    query.message.reply_text(
            f'Activity {activity.activity_name} was deleted ❌'
        )
    
    # Get new user input
    return wait_for_input(update, context)


#TODO: Implement handling of stop command
def cancel(update:Update, context):
    update.message.reply_text(
        f'Ok. Bye 😕'
    )

# /show_score - Shows Leaderboard score 
def show_score_command_handler(update:Update, context):

    chat_id = update.effective_chat.id
    leaderboard = get_leaderboard_by_id(leaderboard_id=chat_id)

    # Create/Update User 
    user = create_user(update, context)
    
    score = get_leaderboard_score(leaderboard_id =leaderboard.id)
    score_message = ''
    if score:
        for indx, row in enumerate(score):
            score_message+= f"{'🥇 ' if indx == 0 else ''}" + f"{row['name']}" +' - '+ f"{row['points']}" + '💎\n  '
        update.message.reply_text(
            score_message
        )
    else:
        update.message.reply_text(
            f'Leaderboard has not started. Send /start to enter the Leaderboard🏆'
        )

    return ConversationHandler.END 

# /show_activities - Shows Leaderboard's Activityes 
def show_activities_command_handler(update:Update, context):
    # Create Leaderboard if do not exists 
    leaderboard = create_leaderboard(update, context)
    # Create/Update User 
    user = create_user(update, context)
    # Get leaderboard activities 
    activities = get_leaderboard_activities(leaderboard_id = leaderboard.id)
    
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


def main():
    project_id = os.environ.get('GCLOUD_PROJECT_ID')

    gcl = gcloud.Gcloud(project_id)
    token = gcl.access_secret_version()

    #Create Updater
    updater = Updater(token=token, use_context=True)
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start),
                     CommandHandler('add_activity', add_activity_command_handler), 
                     CommandHandler('execute_activity', execute_activity_command_handler), 
                     CommandHandler('show_score', show_score_command_handler), 
                     CommandHandler('show_activities', show_activities_command_handler)], 
        states = {
            ACTIVITY : [ MessageHandler(Filters.all, add_activity, pass_user_data=True)],
            POINTS : [MessageHandler(Filters.all, add_points, pass_user_data=True)], 
            IDLE : [CallbackQueryHandler( idle,  pass_user_data=True)], 
            DELETE : [CallbackQueryHandler(delete, pass_user_data=True)],
            EXECUTE_ACTIVITY : [CallbackQueryHandler(execute_activity, pass_user_data=True)]
        }, 
        fallbacks=[CommandHandler('start', start), 
                 CommandHandler('execute_activity', execute_activity_command_handler), 
                 CommandHandler('add_activity', add_activity_command_handler), 
                 CommandHandler('show_score', show_score_command_handler), 
                 CommandHandler('show_activities', show_activities_command_handler)]
    )

    #TODO: Implement /stop command 

    
    #Create Dispatcher
    disp = updater.dispatcher

    #Add handlers to updater
    disp.add_handler(conv_handler)

    #Init database
    init_db() 

    #Start polling from Telegram
    updater.start_polling()

    updater.idle()




if __name__ == "__main__":
    main() 





