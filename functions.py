# -*- coding: utf-8 -*-
from pymysql import MySQLError

import settings
import pymysql.cursors
# Telegram
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, Filters, MessageHandler, CommandHandler, CallbackQueryHandler, RegexHandler, CallbackContext
from telegram.error import (
    TelegramError, Unauthorized, BadRequest, TimedOut, ChatMigrated, NetworkError)

# System libraries
from datetime import date, datetime, timedelta
import random
import requests

# Others
import logging
import pytz


def query(sql):
    try:
        with settings.db_connection.cursor() as cursor:
            cursor.execute(sql)
            if not(sql.startswith("SELECT")):
                settings.db_connection.commit()
            return cursor.fetchall()
    except MySQLError as e:
        print('Got error {!r}, errno is {}'.format(e, e.args[0]))
        return False

def subscribe_course(update: Update, context: CallbackContext):
    printYears(context)

def subscribed_subject_text_list(update: Update, context: CallbackContext):
    msg = "";
    for subject in subscribed_subject(context.message.chat_id):
        msg += "✅  " + subject.split("|")[0] + "\n\n"
    if msg is "":
        msg = "Non sei iscritto a nessun corso"
    context.message.reply_text(msg)


def subscribed_subject(chat_id):
    subscribedSubject = []
    res = query("SELECT * FROM Iscrizioni WHERE chat_id=" + str(chat_id))
    for record in res:
        for materia in settings.materie:
            if record["codice_corso"] == materia["codice_corso"]:
                subscribedSubject.append(str(materia["nome"]) + "|" + str(materia["codice_corso"]))
    return subscribedSubject


def confirm_subscription(chat_id, codice_corso, context, data):
    query("INSERT INTO `Iscrizioni` (`chat_id`,`codice_corso`) VALUES (" + str(chat_id) + "," + str(codice_corso) + ");")
    printConfirmedSubscription(context, data)

def confirm_unsubscription(chat_id, codice_corso, context, data):
    query("DELETE FROM Iscrizioni WHERE chat_id=" + str(chat_id) + " AND codice_corso=" + str(codice_corso))
    printConfirmedUnsubscription(context)

def unsubscribe_course(update: Update, context: CallbackContext):
    printUnsubscribe(context)

def printUnsubscribe(context: CallbackContext, firstCall=True):
    names = []
    values = []
    chat_id = context.message.chat_id if firstCall else context.callback_query.message.chat_id
    for subject in subscribed_subject(chat_id):
        names.append(str(subject.split("|")[0]))
        values.append("dis=" + str(subject.split("|")[1]))
    printKeyboard(context, names, values, "", "Seleziona la materia da cui vuoi disiscriverti", 1, reply=firstCall)


def buttonHandler(update: Update, context: CallbackContext):
    query = context.callback_query
    data = query.data
    print("query data = " + data)
    if data.startswith('year'):
        if data[len(data)-1] is "|":
            data = data[:-1]
        year = data.split('=')[1]
        printDepartment(context, year, data)
    elif data.startswith('dep'):
        department = (data.split('|')[0]).split('=')[1]
        year       = (data.split('|')[1]).split('=')[1]
        printCdS(context, year, department, data)
    elif data.startswith('cds'):
        cds        = (data.split('|')[0])
        max_anno   = int(((data.split('|')[0]).split('=')[1]).split('_')[1])
        department = (data.split('|')[1])
        year       = (data.split('|')[2])
        data = cds + '|' + department + '|' + year
        printCourseYears(context, max_anno, data)
    elif data.startswith('cy'):
        printSemester(context, data)
    elif data.startswith('sem'):
        semester   = (data.split('|')[0]).split('=')[1]
        courseyear = (data.split('|')[1]).split('=')[1]
        cds        = (data.split('|')[2]).split('=')[1]
        department = (data.split('|')[3]).split('=')[1]
        year       = (data.split('|')[4]).split('=')[1]
        printSubject(context, year, department, cds[:-2], courseyear, semester, data)
    elif data.startswith('sj'):
        subject = (data.split('|')[0]).split('=')[1]
        printChoiceSubscription(context, subject, data)
    elif data.startswith('confSub'):
        chat_id = context.callback_query.message.chat_id
        codice_corso = (data.split('|')[1]).split('=')[1]
        confirm_subscription(chat_id, codice_corso, context, data)
    elif data.startswith("confDis"):
        chat_id = context.callback_query.message.chat_id
        codice_corso = (data.split('|')[1]).split('=')[1]
        confirm_unsubscription(chat_id, codice_corso, context, codice_corso)
    elif data == "reload_printYears":
        printYears(context, False)
    elif data == "reload_dis":
        printUnsubscribe(context, firstCall= False)
    elif data.startswith("dis"):
        if data[len(data)-1] is "|":
            data = data[:-1]
        chat_id = context.callback_query.message.chat_id
        codice_corso = (data.split('|')[0]).split('=')[1]
        printChoiceSubscription(context, codice_corso, data, dis=True)
    elif data == "Esc":
        chat_id = context.callback_query.message.chat_id
        message_id = context.callback_query.message.message_id
        update.deleteMessage(chat_id= chat_id, message_id= message_id)

def printYears(context: CallbackContext, firstCall=True):
    september = 9
    nYearsButtons = 3
    options = []
    values = []
    val = 0
    tz = pytz.timezone('Europe/Rome')
    time = datetime.now(tz)
    checkNewYear = datetime(year=time.year, month=september, day=1)
    checkNewYear = tz.localize(checkNewYear)
    if time > checkNewYear:
        val = 1
    for x in range(nYearsButtons):
        options.insert(0, str(time.year - (1-val) - x) + "/" + str((time.year + val) - x))
        values.insert(0, "year=" + str((time.year + val) - x))
    printKeyboard(context, options, values, "", "Seleziona l\'anno accademico:", 3, reply=firstCall)

def printDepartment(context, year, data):
    names = []
    values = []
    for dipartimento in settings.dipartimenti:
        if str(dipartimento["anno_accademico"]) == str(year):
            names.append(dipartimento["nome"])
            values.append("dep=" + dipartimento["id"])
    printKeyboard(context, names, values, data, "Scegli il dipartimento:", 3)

def getMaxAnno(nome : str):
    if nome.find("LM", 0, len(nome)) is not -1:
        return 2
    else:
        return 3

def printSemester(context, data):
    names = []
    values = []
    for i in range(2):
        names.append(str(i+1) + "° semestre")
        values.append("sem=" + str(i+1))
    printKeyboard(context, names, values, data, "Scegli il semestre:", 2)

def printCdS(context, year, department, data):
    names = []
    values = []
    for corso in settings.cds:
        if str(corso["anno_accademico"]) == str(year) and str(corso["id_dipartimento"]) == str(department):
            max_anno = getMaxAnno(corso["nome"])
            names.append(corso["nome"])
            values.append("cds=" + str(corso["id"]) + "_" + str(max_anno))
    printKeyboard(context, names, values, data, "Scegli il corso di studio:", 2)

def printCourseYears(context, max_anno : int, data : str):
    names = []
    values = []
    for i in range(max_anno):
        names.append(str(i+1) +  "° anno")
        values.append("cy=" + str(i+1))
    printKeyboard(context, names, values, data, "Scegli l\'anno della materia:", max_anno)

def printSubject(context, year, department, cds, courseyear, semester, data):
    names = []
    values = []
    for materia in settings.materie:
        if str(materia["anno_accademico"]) == str(year) and str(materia["id_cds"]) == str(cds):
            if(str(materia["anno"]) == str(courseyear)):
                #if(str(materia["semestre"]) == str(semester)):
                    names.append(materia["nome"])
                    values.append("sj=" + str(materia["codice_corso"]))
    printKeyboard(context, names, values, data, "Scegli la materia:", 1)

def printChoiceSubscription(context, subject, oldData, dis=False):
    keyboard = [[InlineKeyboardButton("Sì", callback_data = "conf" + ("Dis" if dis else "Sub") + "|" + oldData),
                 InlineKeyboardButton("No", callback_data = ("reload_dis" if dis else oldData.split("|", 1)[1]))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    name = ""
    for materia in settings.materie:
        if str(materia["codice_corso"]) == str(subject):
            name = materia["nome"]
    context.callback_query.edit_message_text("Vuoi " + ("di" if dis else "i") + "scriverti a " + name + "?", reply_markup=reply_markup)

def printConfirmedSubscription(context, oldData):
    keyboard = [[InlineKeyboardButton("Altre iscrizioni", callback_data = oldData.split('|', 2)[2]),
                 InlineKeyboardButton("Esci", callback_data= 'Esc')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.callback_query.edit_message_text("Iscrizione avvenuta con successo!", reply_markup=reply_markup)

def printConfirmedUnsubscription(context):
    context.callback_query.edit_message_text("Discrizione avvenuta con successo!")

def printKeyboard(context, listToPrint, callbackValues, oldData, msg, nButRow, reply=False):
    keyboard = getKeyboard(listToPrint, callbackValues, oldData, nButRow)
    reply_markup = InlineKeyboardMarkup(keyboard)
    if reply:
        context.message.reply_text(msg, reply_markup=reply_markup)
    else:
        context.callback_query.edit_message_text(msg, reply_markup=reply_markup)

def getKeyboard(options, values, oldData, nButRow):
    i = 1
    keyboard = [[]]
    kb = []
    for element, value in zip(options, values):
        kb.append(InlineKeyboardButton(element, callback_data = value + "|" + oldData))
        if i % nButRow == 0 or i == len(options):
            keyboard.append(kb)
            kb = []
        i += 1
    if oldData != "":
        if oldData.find("|") == -1:
            keyboard.append([InlineKeyboardButton("Torna indietro 🔙", callback_data = "reload_printYears"),
                            InlineKeyboardButton("Esci", callback_data = "Esc")])
        else:
            keyboard.append([InlineKeyboardButton("Torna indietro 🔙", callback_data= oldData.split("|", 1)[1]),
                             InlineKeyboardButton("Esci", callback_data="Esc")])
    return keyboard