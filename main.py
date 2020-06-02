import logging

import telegram
from telegram import (Update, Message, InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (Updater, MessageHandler, CommandHandler, ConversationHandler, Filters, CallbackQueryHandler)

import os 

from model import (Activity, init_db, get_activities_by_user_id, get_activity_by_id, delete_activity_by_id,
                    Leaderboard, get_leaderboard_by_id, 
                    User, get_user_by_id, 
                    Participant, get_participant_by_user_id_and_leaderboard_id)
import gcloud


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)

ACTIVITY, POINTS, IDLE, DELETE, USER_INPUT  = range(5) 


#TODO: Implement commands
# /show_score
# /show_activities
# /add_activity
# /perform_activity

#TODO: Reserch how to show list of the commands to the user

#TODO: Implement perform_activity action and command

def start(update: Update, context):

    update.message.reply_text(
        'Ok, let\'s start'
    )

    # """
    # Create Leaderboard if do not exists 
    # Update Leaderboard if exists
    # """
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

    # """
    # Check if User is db, create if not, update is yes
    # """
    user_id = update.effective_user.id
    user_name = update.effective_user.username
    user = get_user_by_id(id=user_id)

    if not user:
        user = User(name=user_name, id=user_id)
    else:
        #Adding this check because user can change the name
        user.name = user_name
    user.save_user()

    # """
    # Add Participant to db if not present
    # """
    participant = get_participant_by_user_id_and_leaderboard_id(user_id = user.id, leaderboard_id=leaderboard.id)

    if not participant: 
        participant = Participant(user_id = user.id, leaderboard_id=leaderboard.id)
        participant.save_participant()

        #If group chat - notify participants that new participant was added 
        if chat_type != 'private':
            update.message.reply_text(
                f'{user.name} was added to the Leaderboard {leaderboard.name}'
            )   

    #TODO: Need to check if any activity is present in leaderboard.
    # Ask to add new activities only in case no activities present  
    update.message.reply_text(
        'Send me the name of a first activity'
    )

    return ACTIVITY

#TODO: Add check if activity with same name.lower() exists
def add_activity(update: Update, context):
    activity = update.message.text
    context.user_data[ACTIVITY] = activity
    update.message.reply_text(
        f'Ok. Activity {context.user_data[ACTIVITY]} added',
        quote = True
    )
    update.message.reply_text(
        f'How many points should I assign for {context.user_data[ACTIVITY]}?'
    )

    return POINTS

def add_points(update: Update, context):
    points = update.message.text
    try:
        int(points) 
    except ValueError:
        update.message.reply_text(
            f'{points} is not a number. Please enter number 😊'
        )
        return POINTS
    else:


        context.user_data[POINTS] = points
        update.message.reply_text(
            f'Ok. Activity {context.user_data[ACTIVITY]} gives {context.user_data[POINTS]} points 😎'
        )

        # Saving activity to the database
        act = Activity(activity_name=context.user_data[ACTIVITY], points=context.user_data[POINTS], author_user_id=update.effective_user.id )
        act.save_activity()

        # Get new user input
        return wait_for_input(update, context)

def wait_for_input(update:Update, context):
    
    #TODO: Add Stop Button
    # Add Show Activities button
    keyboard = [
        [InlineKeyboardButton("➕ Add Activity", callback_data=0)], 
        [InlineKeyboardButton("➖ Delete Activity", callback_data=1)]
    ]

    keyboard_markup = InlineKeyboardMarkup(keyboard)

    # Send update to the user
    # Check if user entered any update
    message_text = f'What would you like to do next? 😏'
    if update.message:
        update.message.reply_text(
            message_text, reply_markup = keyboard_markup
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

        query.message.reply_text(
            f'Ok, send me name of the Activity?'
        )
        return ACTIVITY
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

        for act in activities:
            key = [InlineKeyboardButton(f'{act.activity_name} - {act.points} points', callback_data=act.id)]
            keyboard.append(key)
        
        keyboard_markup = InlineKeyboardMarkup(keyboard)
        
        query.message.reply_text(
            f'What Acitivity you would like to delete?', reply_markup=keyboard_markup
        )

        return DELETE

#TODO: Ensure that once Activity is deleted all Performed_Activity entities are deleted as well 
# Check if any Performed_Activity entities exists. If Yes ask for confirmation 
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
    upldate.message.reply_text(
        f'Ok. Bye 😕'
    )


def main():
    project_id = os.environ.get('GCLOUD_PROJECT_ID')

    gcl = gcloud.Gcloud(project_id)
    token = gcl.access_secret_version()

    #Create Updater
    updater = Updater(token=token, use_context=True)
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states = {
            ACTIVITY : [ MessageHandler(Filters.all, add_activity, pass_user_data=True)], 
            POINTS : [MessageHandler(Filters.all, add_points, pass_user_data=True)], 
            IDLE : [CallbackQueryHandler( idle,  pass_user_data=True)], 
            DELETE : [CallbackQueryHandler(delete, pass_user_data=True)],
            # USER_INPUT : [CallbackQueryHandler(delete, pass_user_data=True)]
        }, 
        fallbacks=[CommandHandler('start', start)]
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





