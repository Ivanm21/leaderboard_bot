import logging

import telegram
from telegram import (Update, Message, InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (Updater, MessageHandler, CommandHandler, ConversationHandler, Filters, CallbackQueryHandler)

import os 

import gcloud

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)

ACTIVITY, POINTS, IDLE = range(3) 

def start(update: Update, context):

    update.message.reply_text(
        'Ok, let\'s start'
    )
    update.message.reply_text(
        'Send me name of the first activity'
    )

    return ACTIVITY

def add_activity(update: Update, context):
    activity = update.message.text
    context.user_data[ACTIVITY] = activity
    update.message.reply_text(
        f'Ok. Activity {context.user_data[ACTIVITY]} added',
        quote = True
    )
    update.message.reply_text(
        f'How much points should I assign for {context.user_data[ACTIVITY]}?'
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
        keyboard = [
            [InlineKeyboardButton("➕ Add Activity", callback_data=1)], 
            [InlineKeyboardButton("➖ Delete Activity", callback_data=2)]
        ]

        keyboard_markup = InlineKeyboardMarkup(keyboard)

        context.user_data[POINTS] = points
        update.message.reply_text(
            f'Ok. Activity {context.user_data[ACTIVITY]} gives {context.user_data[POINTS]} points 😎'
        )
        
        update.message.reply_text(
            f'What would you like to do next? 😏', reply_markup = keyboard_markup
        )

    return IDLE

def idle(update:Update, context):
    
    query = update.callback_query
    query.answer()

    if query.data == '1': 
        query.edit_message_text(
            f'Ok, send me name of the Activity?'
        )
        return ACTIVITY
    elif query.data == '2': 
        query.edit_message_text(
            f'What Acitivity you would like to delete?{context.user_data}'
        )





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
            IDLE : [CallbackQueryHandler( idle,  pass_user_data=True)]
        }, 
        fallbacks=[CommandHandler('start', start)]
    )


    #Create Dispatcher
    disp = updater.dispatcher

    #Add handlers to updater
    disp.add_handler(conv_handler)



    #Start polling from Telegram
    updater.start_polling()

    updater.idle()




if __name__ == "__main__":
    main() 





