import logging
import postgresql
import time

import checker

from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, ConversationHandler)

logging.basicConfig(filename='logs.txt', filemode='w', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
 
logger = logging.getLogger('EGElog')

AGREE, SERIAL, NUMBER, EXAM = range(4)

db = postgresql.open('.......')

insertDB = db.prepare("INSERT INTO t_user.telegram_data (chat_id, pass_ser, pass_num, exam) VALUES ($1, $2, $3, $4)")

eraseDB = db.prepare("DELETE FROM t_user.telegram_data WHERE chat_id = $1")

def start(bot, update):
    update.message.reply_text(
        'Привет, {}!\nДавай я помогу тебе узнать твои результаты ЕГЭ раньше всех!\nВнимание! Я работаю только в Краснодарском крае и узнаю результаты с краевого сайта, а не всероссийского.\nЭто означает, что результаты ты узнаешь раньше, но они будут нести предварительный характер.\nНадеюсь, моему сообщению с твоими баллами ты будешь рад!\nМне понадобятся серия и номер твоего паспорта для проверки наличия результатов.\nНо для начала мне нужно твое согласие на обработку персональных данных.\nВведи \'Да\' или \'Нет\''.format(update.message.from_user.first_name)
    )
    return AGREE

def getAgree(bot, update):
    user = update.message.from_user
    logger.info("Agree of %s: %s", user.first_name, update.message.text)
    ans = update.message.text

    if ans == 'Нет':
        update.message.reply_text("Это твое право, но если передумаешь - введи /start")
        return ConversationHandler.END

    if ans != 'Да':
        update.message.reply_text("Может опечатка? Если захочешь начать сначала - введи /start")
        return ConversationHandler.END

    update.message.reply_text("Великолепно! Теперь введи серию своего паспорта без пробелов.")
    return SERIAL

def getSerial(bot, update, chat_data):
    user = update.message.from_user
    logger.info("Serial of %s: %s", user.first_name, update.message.text)

    if len(update.message.text) != 4 or not update.message.text.isdigit():
        update.message.reply_text("Ну нет, это явно не серия паспорта. Если захочешь попробовать еще раз - пиши /start")
        return ConversationHandler.END

    chat_data['ser'] = update.message.text
    update.message.reply_text("Спасибо!\nОстался номер паспорта. Снова без пробелов.")
    return NUMBER

def getNumber(bot, update, chat_data):
    user = update.message.from_user
    logger.info("Number of %s: %s", user.first_name, update.message.text)

    if len(update.message.text) != 6 or not update.message.text.isdigit():
        update.message.reply_text("Ну нет, это явно не номер паспорта. Если захочешь попробовать еще раз - пиши /start")
        return ConversationHandler.END

    chat_data['num'] = update.message.text
    update.message.reply_text("Прекрасно! Теперь укажи предмет, который хочешь отслеживать. Напиши название с большой буквы (Надеюсь, за русский баллы у тебя будут хорошие, и ты напишешь без ошибок). Пример: Русский язык или Математика")
    return EXAM

def getNumOfExam(ex):
    if (ex == "Русский язык"):
        return "1"
    if (ex == "Математика"):
        return "2"
    if (ex == "Обществознание"):
        return "12"
    if (ex == "Физика"):
        return "3"
    if (ex == "Химия"):
        return "4"
    if (ex == "Информатика"):
        return "5"
    if (ex == "Биология"):
        return "6"
    if (ex == "История"):
        return "7"
    if (ex == "Литература"):
        return "13"
    if (ex == "География"):
        return "8"
    if (ex == "Английский язык"):
        return "9"
    if (ex == "Немецкий язык"):
        return "10"
    if (ex == "Французский язык"):
        return "11"
    return "-1"

def check(bot, job):
    userData = job.context[1]
    chat_id = job.context[0]

    answer = checkerEGE.getCurrentState(userData['exam'], userData['ser'], userData['num'])

    if answer != 'Результатов нет!' and answer != 'Внимание! Необходимо заполнить все поля формы!' and answer != 'Ошибка! Вы ввели неверный код!':

        bot.send_message(job.context[0], text="Кажется, результаты пришли!\nhttp://gas.kubannet.ru/?m=114")
        bot.send_message(job.context[0], text="Твой вторичный балл: " + answer)

        logger.info("RESULT of %s: %s", user.first_name, answer)

        curJob = userData['job']
        curJob.schedule_removal()
        del userData['job']

        eraseDB(str(chat_id))

        bot.send_message(job.context[0], text="Чтобы начать отслеживать новый предмет - пиши /start")

def getExam(bot, update, job_queue, chat_data):
    user = update.message.from_user
    chat_id = update.message.chat_id

    logger.info("Exam of %s: %s", user.first_name, update.message.text)

    examNum = getNumOfExam(update.message.text)

    if examNum == "-1":
        update.message.reply_text("Я о таком экзамене пока не слышал. Может просто маленькая опечатка? Если захочешь попробовать еще раз - пиши /start")
        return ConversationHandler.END

    chat_data['exam'] = examNum
    update.message.reply_text("Отлично! Теперь я пришлю тебе сообщение, когда появятся твои результаты.")

    job = job_queue.run_repeating(check, 1000, first=0, context=[chat_id, chat_data])
    chat_data['job'] = job

    insertDB(str(chat_id), chat_data['ser'], chat_data['num'], chat_data['exam'])

    return ConversationHandler.END

def cancel(bot, update):
    return ConversationHandler.END

def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)

def restartPostgres(bot, update, job_queue):
    users = db.query("SELECT * FROM t_user.telegram_data")
    for user in users:

        chat_data = dict()
        chat_data['ser'] = user['pass_ser']
        chat_data['num'] = user['pass_num']
        chat_data['exam'] = user['exam']

        chat_data['job'] = job_queue.run_repeating(check, 1000, first=0, context=[user['chat_id'], chat_data])

        update.message.reply_text("Добавлен " + str(user['chat_id']))

        time.sleep(2)

def main():
    updater = Updater("...")

    dp = updater.dispatcher

    convHandlerData = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            AGREE: [MessageHandler(Filters.text, getAgree)],

            SERIAL: [MessageHandler(Filters.text, getSerial, pass_chat_data=True)],

            NUMBER: [MessageHandler(Filters.text, getNumber, pass_chat_data=True)],

            EXAM: [MessageHandler(Filters.text, getExam, pass_chat_data=True, pass_job_queue=True)]
        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(CommandHandler("restartPostgres", restartPostgres, pass_job_queue=True))
    dp.add_handler(convHandlerData)

    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
