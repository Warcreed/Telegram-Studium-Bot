# -*- coding: utf-8 -*-
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters

from functions import *
from settings import *
from Modules.Keyboard import printDefaultKeyboard

from Modules.Iscrizioni import *
from Modules.Disiscrizioni import *
from Modules.Keyboard import *

def main():
    updater = Updater(TOKEN, request_kwargs={'read_timeout': 20, 'connect_timeout': 20}, use_context=True)
    
    dp = updater.dispatcher
    #dp.add_handler(MessageHandler(Filters.all, logging_message),1)
    dp.add_handler(CommandHandler('start', printDefaultKeyboard))
    dp.add_handler(CommandHandler('studium', printMenu))
    dp.add_handler(CommandHandler('help', getHelp)) 
       
    dp.add_handler(MessageHandler(Filters.regex('📚 Studium'), printMenu))
    dp.add_handler(MessageHandler(Filters.regex('❓ Help'), getHelp))

    dp.add_handler(MessageHandler(Filters.regex('✅ Iscriviti'), printYears))
    dp.add_handler(MessageHandler(Filters.regex('❌ Disiscriviti'), printUnsubscribe))
    dp.add_handler(MessageHandler(Filters.regex('📚 Mie iscrizioni'), subscribed_subject_text_list))
    dp.add_handler(MessageHandler(Filters.regex('🔙 Torna indietro'), printDefaultKeyboard))
    #dp.add_handler(CallbackQueryHandler(callback))
    dp.add_handler(CallbackQueryHandler(buttonHandler))

    read_db_conf()
    read_remote_db()
    job_minute = updater.job_queue.run_repeating(forwardNotices, interval=30, first=0)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()