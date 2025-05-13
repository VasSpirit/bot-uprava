import os
import logging
import smtplib
import mimetypes
import base64
from datetime import datetime
from email.message import EmailMessage
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from weasyprint import HTML
import requests
import config
from config import API_URL
from config import TOKEN
from config import UPLOAD_FOLDER
from config import PDF_FOLDER
from config import FILE_LIMIT_MB
from config import FILE_LIMIT_BYTES

user_data = {}

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


# Клавиатуры
def get_main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📝 Начать новое обращение")],
        [KeyboardButton("ℹ️ Помощь")]
    ], resize_keyboard=True)


def get_appeal_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📤 Отправить обращение")],
        [KeyboardButton("❌ Отменить обращение")],
        [KeyboardButton("🏠 Главное меню")]
    ], resize_keyboard=True)


# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_data[chat_id] = {
        'messages': [],
        'images': [],
        'videos': [],
        'audios': [],
        'locations': []
    }

    welcome_text = (
        "👋 Добро пожаловать в бот управы округа!\n\n"
        "Здесь вы можете оставить обращение по вопросам:\n"
        "• ЖКХ и благоустройства\n"
        "• Дорожного хозяйства\n"
        "• Социальной поддержки\n\n"
        "Нажмите «📝 Начать новое обращение» чтобы продолжить"
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=welcome_text,
        reply_markup=get_main_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "ℹ️ Справка по работе с ботом:\n\n"
        "1. Нажмите «📝 Начать новое обращение»\n"
        "2. Напишите текст обращения\n"
        "3. При необходимости приложите:\n"
        "   • Фото/видео проблемы\n"
        "   • Голосовое сообщение\n"
        "   • Геолокацию места\n"
        "4. Нажмите «📤 Отправить обращение»\n\n"
        "Вы можете отменить обращение в любой момент"
    )

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=help_text,
        reply_markup=get_main_keyboard()
    )


# Обработчики сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text

    if chat_id not in user_data:
        user_data[chat_id] = {
            'messages': [],
            'images': [],
            'videos': [],
            'audios': [],
            'locations': []
        }

    if text == "📝 Начать новое обращение":
        user_data[chat_id] = {
            'messages': [],
            'images': [],
            'videos': [],
            'audios': [],
            'locations': []
        }
        await context.bot.send_message(
            chat_id=chat_id,
            text="✍️ Напишите текст вашего обращения. Вы можете приложить фото, видео, аудио или геолокацию.",
            reply_markup=get_appeal_keyboard()
        )

    elif text == "📤 Отправить обращение":
        await submit_appeal(update, context)

    elif text == "❌ Отменить обращение":
        user_data[chat_id] = {
            'messages': [],
            'images': [],
            'videos': [],
            'audios': [],
            'locations': []
        }
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Текущее обращение отменено",
            reply_markup=get_main_keyboard()
        )

    elif text == "🏠 Главное меню":
        await context.bot.send_message(
            chat_id=chat_id,
            text="Вы вернулись в главное меню",
            reply_markup=get_main_keyboard()
        )

    elif text == "ℹ️ Помощь":
        await help_command(update, context)

    else:
        # Обычное текстовое сообщение
        user_data[chat_id]['messages'].append(text)
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Сообщение добавлено к обращению. Вы можете продолжить или отправить обращение.",
            reply_markup=get_appeal_keyboard()
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_data:
        await start(update, context)
        return

    photo = update.message.photo[-1]  # Берем самое качественное фото
    file_id = photo.file_id
    response = requests.get(f'{API_URL}/getFile?file_id={file_id}')
    data = response.json()['result']
    file_url = f'https://api.telegram.org/file/bot{TOKEN}/{data["file_path"]}'
    filename = os.path.join(UPLOAD_FOLDER, f"{chat_id}_photo_{len(user_data[chat_id]['images']) + 1}.jpg")

    r = requests.get(file_url)
    with open(filename, 'wb') as img_file:
        img_file.write(r.content)

    user_data[chat_id]['images'].append(filename)
    await context.bot.send_message(
        chat_id=chat_id,
        text="✅ Фото добавлено к обращению",
        reply_markup=get_appeal_keyboard()
    )


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_data:
        await start(update, context)
        return

    video = update.message.video
    file_id = video.file_id

    try:
        # Проверка размера файла
        file_size = await check_file_size(file_id)
        if file_size > FILE_LIMIT_BYTES:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Размер видео превышает допустимый лимит (100 МБ)",
                reply_markup=get_appeal_keyboard()
            )
            return

        # Скачивание видео
        response = requests.get(f'{API_URL}/getFile?file_id={file_id}')
        data = response.json()['result']
        file_url = f'https://api.telegram.org/file/bot{TOKEN}/{data["file_path"]}'
        filename = os.path.join(UPLOAD_FOLDER, f"{chat_id}_video_{len(user_data[chat_id]['videos']) + 1}.mp4")

        r = requests.get(file_url)
        with open(filename, 'wb') as vid_file:
            vid_file.write(r.content)

        user_data[chat_id]['videos'].append(filename)
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Видео добавлено к обращению",
            reply_markup=get_appeal_keyboard()
        )

    except Exception as e:
        logger.error(f"Ошибка обработки видео: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Не удалось обработать видео. Попробуйте другое видео.",
            reply_markup=get_appeal_keyboard()
        )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_data:
        await start(update, context)
        return

    voice = update.message.voice
    file_id = voice.file_id

    try:
        # Проверка размера файла
        file_size = await check_file_size(file_id)
        if file_size > FILE_LIMIT_BYTES:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Размер аудио превышает допустимый лимит (100 МБ)",
                reply_markup=get_appeal_keyboard()
            )
            return

        # Скачивание аудио
        response = requests.get(f'{API_URL}/getFile?file_id={file_id}')
        data = response.json()['result']
        file_url = f'https://api.telegram.org/file/bot{TOKEN}/{data["file_path"]}'
        filename = os.path.join(UPLOAD_FOLDER, f"{chat_id}_audio_{len(user_data[chat_id]['audios']) + 1}.ogg")

        r = requests.get(file_url)
        with open(filename, 'wb') as audio_file:
            audio_file.write(r.content)

        user_data[chat_id]['audios'].append(filename)
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Аудиосообщение добавлено к обращению",
            reply_markup=get_appeal_keyboard()
        )

    except Exception as e:
        logger.error(f"Ошибка обработки аудио: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Не удалось обработать аудиосообщение. Попробуйте еще раз.",
            reply_markup=get_appeal_keyboard()
        )


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_data:
        await start(update, context)
        return

    location = update.message.location
    lat, lon = location.latitude, location.longitude
    user_data[chat_id]['locations'].append(f"{lat},{lon}")

    await context.bot.send_message(
        chat_id=chat_id,
        text="✅ Геолокация добавлена к обращению",
        reply_markup=get_appeal_keyboard()
    )

async def submit_appeal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_info = user_data.get(chat_id, {})

    if not user_info.get('messages'):
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Нельзя отправить пустое обращение. Напишите текст обращения.",
            reply_markup=get_appeal_keyboard()
        )
        return

    # Формируем текст обращения
    appeal_text = "\n".join(user_info['messages'])
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        # Генерируем PDF
        pdf_filename = generate_pdf(
            chat_id=chat_id,
            appeal_text=appeal_text,
            current_date=current_date,
            images=user_info.get('images', []),
            locations=user_info.get('locations', [])
        )

        # Отправляем email
        send_email(
            appeal_text,
            pdf_filename,
            chat_id,
            current_date,
            videos=user_info.get('videos', []),
            audios=user_info.get('audios', [])
        )

        # Очищаем данные пользователя
        user_data[chat_id] = {
            'messages': [],
            'images': [],
            'videos': [],
            'audios': [],
            'locations': []
        }

        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Ваше обращение успешно отправлено! Спасибо за обратную связь.",
            reply_markup=get_main_keyboard()
        )

    except Exception as e:
        logger.error(f"Ошибка при отправке обращения: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Произошла ошибка при отправке обращения. Пожалуйста, попробуйте позже.",
            reply_markup=get_main_keyboard()
        )


def send_email(appeal_text, pdf_filename, chat_id, date, videos=None, audios=None):
    sender = config.SENDER_EMAIL
    receivers = config.RECEIVER_EMAILS
    subject = f"Обращение #{chat_id} от {date}"

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ', '.join(receivers)

    # Текст письма
    msg.set_content(f"""
    Новое обращение из Telegram-бота:

    ID чата: {chat_id}
    Дата: {date}
    Текст обращения:
    {appeal_text}

    Подробности в прикрепленном PDF-файле.
    """)

    # Прикрепляем PDF
    with open(pdf_filename, 'rb') as f:
        msg.add_attachment(
            f.read(),
            maintype='application',
            subtype='pdf',
            filename=f"Обращение_{chat_id}.pdf"
        )

    # Прикрепляем медиафайлы из user_data
    user_info = user_data.get(chat_id, {})

    # Прикрепляем видео
    for video_path in user_info.get('videos', []):
        try:
            with open(video_path, 'rb') as f:
                content_type, _ = mimetypes.guess_type(video_path)
                if content_type:
                    maintype, subtype = content_type.split('/')
                else:
                    maintype, subtype = 'video', 'mp4'
                msg.add_attachment(
                    f.read(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=os.path.basename(video_path)
                )
        except Exception as e:
            logger.error(f"Ошибка прикрепления видео {video_path}: {e}")

    # Прикрепляем аудио
    for audio_path in user_info.get('audios', []):
        try:
            with open(audio_path, 'rb') as f:
                content_type, _ = mimetypes.guess_type(audio_path)
                if content_type:
                    maintype, subtype = content_type.split('/')
                else:
                    maintype, subtype = 'audio', 'ogg'
                msg.add_attachment(
                    f.read(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=os.path.basename(audio_path)
                )
        except Exception as e:
            logger.error(f"Ошибка прикрепления аудио {audio_path}: {e}")

    # Отправка через SMTP
    try:
        with smtplib.SMTP_SSL('smtp.mail.ru', 465) as server:
            server.login(sender, config.EMAIL_PASSWORD)
            server.send_message(msg)
        logger.info(f"Письмо для обращения {chat_id} отправлено")

        # Удаляем файлы после успешной отправки
        for video_path in user_info.get('videos', []):
            try:
                os.remove(video_path)
            except Exception as e:
                logger.error(f"Ошибка удаления видео {video_path}: {e}")

        for audio_path in user_info.get('audios', []):
            try:
                os.remove(audio_path)
            except Exception as e:
                logger.error(f"Ошибка удаления аудио {audio_path}: {e}")

    except Exception as e:
        logger.error(f"Ошибка отправки письма: {e}")
        raise

async def handle_video_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_data:
        await start(update, context)
        return

    video_note = update.message.video_note
    file_id = video_note.file_id

    try:
        # Проверка размера файла
        file_size = await check_file_size(file_id)
        if file_size > FILE_LIMIT_BYTES:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Размер видео-кружка превышает допустимый лимит (100 МБ)",
                reply_markup=get_appeal_keyboard()
            )
            return

        # Скачивание видео-кружка
        response = requests.get(f'{API_URL}/getFile?file_id={file_id}')
        data = response.json()['result']
        file_url = f'https://api.telegram.org/file/bot{TOKEN}/{data["file_path"]}'
        filename = os.path.join(UPLOAD_FOLDER, f"{chat_id}_video_note_{len(user_data[chat_id]['videos']) + 1}.mp4")

        r = requests.get(file_url)
        with open(filename, 'wb') as vid_file:
            vid_file.write(r.content)

        user_data[chat_id]['videos'].append(filename)
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Видео-кружок добавлен к обращению",
            reply_markup=get_appeal_keyboard()
        )

    except Exception as e:
        logger.error(f"Ошибка обработки видео-кружка: {e}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Не удалось обработать видео-кружок. Попробуйте другое видео.",
            reply_markup=get_appeal_keyboard()
        )

def generate_pdf(chat_id, appeal_text, current_date, images=None, locations=None):
    """Генерирует PDF из текста обращения, изображений и геолокаций"""
    images = images or []
    locations = locations or []

    # Формируем HTML
    body_html = f"""
    <h1>Обращение с Telegram № {chat_id}</h1>
    <p><strong>Дата обращения:</strong> {current_date}</p>
    <div style="margin: 20px 0; padding: 15px; background: #f5f5f5; border-radius: 5px;">
        {appeal_text.replace('\n', '<br>')}
    </div>
    """

    # Добавляем изображения
    for i, img_path in enumerate(images, 1):
        with open(img_path, 'rb') as img_file:
            encoded = base64.b64encode(img_file.read()).decode('utf-8')
            mime = mimetypes.guess_type(img_path)[0] or 'image/jpeg'
            body_html += f'<h3>Фото {i}</h3><img src="data:{mime};base64,{encoded}" style="max-width: 100%;"/>'

    # Добавляем геолокации
    if locations:
        body_html += '<h3>Геолокации:</h3>'
        for i, loc in enumerate(locations, 1):
            lat, lon = loc.split(',')
            google_url = f"https://maps.google.com/?q={lat},{lon}"
            yandex_url = f"https://yandex.ru/maps/?ll={lon},{lat}&z=16"
            body_html += f"""
            <div style="margin-bottom: 15px;">
                <p><strong>Место {i}:</strong> Широта: {lat}, Долгота: {lon}</p>
                <p>
                    <a href="{google_url}" target="_blank">Открыть в Google Maps</a> | 
                    <a href="{yandex_url}" target="_blank">Открыть в Яндекс.Картах</a>
                </p>
            </div>
            """

    # Генерируем PDF
    html = HTML(string=body_html)
    pdf_filename = os.path.join(PDF_FOLDER, f"appeal_{chat_id}_{current_date.replace(':', '-')}.pdf")
    os.makedirs(PDF_FOLDER, exist_ok=True)
    html.write_pdf(pdf_filename)

    return pdf_filename

async def check_file_size(file_id):
    response = requests.get(f'{API_URL}/getFile?file_id={file_id}')
    data = response.json()['result']
    return int(data['file_size'])


# Регистрация обработчиков
def main():
    application = ApplicationBuilder().token(config.TOKEN).build()

    # Обработчики команд
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))

    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_video_note))
    application.add_handler(MessageHandler(filters.VIDEO_NOTE, handle_video_note))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))

    application.run_polling()

if __name__ == '__main__':
    main()