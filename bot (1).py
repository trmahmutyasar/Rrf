import os, hashlib, platform, time, sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError, NetworkError, BadRequest

TOKEN = "8412276799:AAFhPZmYJzr9OpxZlqNgEZKNQ6Ft10E1650"
current_dir = os.getcwd()
file_map = {}
history_back = []
history_forward = []
MAX_BUTTONS = 50  # Her mesajda max 50 dosya
offsets = {}      # Kullanıcıya göre sayfa offset

# ----------------- BOT FONKSİYONLARI -----------------
def get_icon(filename, is_dir=False):
    if is_dir: return "📂"
    ext = filename.lower().split('.')[-1]
    if ext in ["mp3","wav","flac","ogg","m4a"]: return "🎵"
    elif ext in ["jpg","jpeg","png","gif","bmp","webp"]: return "🖼️"
    else: return "📄"

def human_readable_size(size):
    for unit in ['B','KB','MB','GB','TB']:
        if size < 1024: return f"{size:.0f}{unit}"
        size /= 1024
    return f"{size:.0f}PB"

def build_file_browser(path, user_id):
    global file_map, offsets
    file_map = {}
    keyboard = []

    try:
        items = os.listdir(path)
        items.sort(key=lambda x: os.path.getmtime(os.path.join(path, x)), reverse=True)
        start = offsets.get(user_id, 0)
        end = min(start + MAX_BUTTONS, len(items))
        current_items = items[start:end]

        for item in current_items:
            key = hashlib.md5(item.encode()).hexdigest()[:10]
            file_map[key] = item
            full_path = os.path.join(path, item)
            icon = get_icon(item, os.path.isdir(full_path))
            info = "" if os.path.isdir(full_path) else human_readable_size(os.path.getsize(full_path))
            mtime = time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(full_path)))
            button_text = f"{icon} {item} | {info} | {mtime}" if info else f"{icon} {item} | {mtime}"
            if os.path.isdir(full_path):
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"cd:{key}")])
            else:
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"get:{key}")])

        nav_buttons = []
        if history_back: nav_buttons.append(InlineKeyboardButton("⬅️ Geri", callback_data="nav_back"))
        if history_forward: nav_buttons.append(InlineKeyboardButton("➡️ İleri", callback_data="nav_forward"))
        if end < len(items): nav_buttons.append(InlineKeyboardButton("➡️ Daha Fazla", callback_data="next_page"))
        if nav_buttons: keyboard.append(nav_buttons)

    except Exception as e:
        keyboard.append([InlineKeyboardButton(f"⚠️ Hata: {e}", callback_data="noop")])

    return keyboard

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    device_info = f"{platform.system()} {platform.release()}, Python {platform.python_version()}"
    offsets[update.effective_user.id] = 0
    keyboard = build_file_browser(current_dir, update.effective_user.id)
    reply_markup_inline = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"📂 Dosya yöneticisine hoş geldin!\nKlasör: {current_dir}\n💻 Cihaz: {device_info}",
        reply_markup=reply_markup_inline
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_dir, file_map, history_back, history_forward, offsets
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    try:
        if data.startswith("cd:"):
            folder = file_map.get(data.split("cd:")[1])
            if folder:
                history_back.append(current_dir)
                history_forward.clear()
                current_dir = os.path.join(current_dir, folder)
                offsets[user_id] = 0

        elif data.startswith("get:"):
            key = data.split("get:")[1]
            filename = file_map.get(key)
            if filename:
                filepath = os.path.join(current_dir, filename)
                if os.path.exists(filepath):
                    await query.message.reply_document(open(filepath, "rb"))

        elif data == "nav_back":
            if history_back:
                history_forward.append(current_dir)
                current_dir = history_back.pop()
                offsets[user_id] = 0

        elif data == "nav_forward":
            if history_forward:
                history_back.append(current_dir)
                current_dir = history_forward.pop()
                offsets[user_id] = 0

        elif data == "next_page":
            offsets[user_id] = offsets.get(user_id, 0) + MAX_BUTTONS

        keyboard = build_file_browser(current_dir, user_id)
        await query.edit_message_text(f"📂 Klasör: {current_dir}", reply_markup=InlineKeyboardMarkup(keyboard))

    except (TelegramError, NetworkError, BadRequest) as e:
        print(f"Hata oluştu: {e}, bot yeniden başlatılıyor...")
        os.execl(sys.executable, sys.executable, *sys.argv)

async def handle_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_dir
    try:
        if context.user_data.get("upload_mode", False):
            if update.message.document:
                file = await update.message.document.get_file()
                filename = update.message.document.file_name
                filepath = os.path.join(current_dir, filename)
                await file.download_to_drive(filepath)
                await update.message.reply_text(f"✅ {filename} yüklendi ({current_dir}) içine kaydedildi.")
                context.user_data["upload_mode"] = False
            else:
                await update.message.reply_text("❌ Lütfen bir dosya gönder.")
    except Exception as e:
        print(f"Upload hatası: {e}, bot yeniden başlatılıyor...")
        os.execl(sys.executable, sys.executable, *sys.argv)

def main():
    while True:
        try:
            app = Application.builder().token(TOKEN).build()
            app.add_handler(CommandHandler("start", start))
            app.add_handler(CallbackQueryHandler(button_handler))
            app.add_handler(MessageHandler(filters.Document.ALL, handle_upload))
            app.run_polling()
        except Exception as e:
            print(f"Bot hata verdi: {e}, yeniden başlatılıyor...")
            time.sleep(2)
            continue

if __name__ == "__main__":
    main()