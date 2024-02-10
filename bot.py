from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy import func, distinct

# Import the database models
from database import Jadwal, AnilistData, Nonton, SessionLocal, engine, Base

API_ID = "7120601"
API_HASH = "aebd45c2c14b36c2c91dec3cf5e8ee9a"
BOT_TOKEN = "5916688383:AAEQmWAhErzCidtIrIIk41VxFgbW0_FnetY"

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Fungsi handler untuk perintah /start
@app.on_message(filters.command("admin"))
async def start_command(client, message):
    # Create buttons for "Manage" and "Jadwal"
    keyboard = [
        [KeyboardButton("Manage"), KeyboardButton("Jadwal")]
    ]

    # Konversi keyboard menjadi objek ReplyKeyboardMarkup
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await message.reply_text("Pilih opsi:", reply_markup=reply_markup)

# Fungsi handler untuk tombol "Manage"
@app.on_message(filters.regex(r'^Manage$'))
async def manage_button_handler(client, message):
    await message.reply_text("Manage button clicked! Implement your manage logic here.")

# Fungsi handler untuk tombol "Jadwal"
@app.on_message(filters.regex(r'^Jadwal$'))
async def jadwal_button_handler(client, message):
    keyboard = [
        ["Senin", "Selasa"],
        ["Rabu", "Kamis"],
        ["Jumat", "Sabtu"],
        ["Minggu"]
    ]

    # Konversi keyboard menjadi objek ReplyKeyboardMarkup
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await message.reply_text("Pilih hari:", reply_markup=reply_markup)

# Fungsi handler untuk pesan teks
@app.on_message(filters.text)
async def text_handler(client, message):
    # Tambahkan logika sesuai dengan pilihan pengguna
    user_input = message.text.lower()

    if user_input in ["senin", "selasa", "rabu", "kamis", "jumat", "sabtu", "minggu"]:
        session = SessionLocal()
        try:
            # Subquery untuk mendapatkan episode terbaru
            subquery = (
                session.query(
                    Nonton.anime_id,
                    func.max(Nonton.episode_number).label("latest_episode")
                )
                .group_by(Nonton.anime_id)
                .subquery()
            )

            # Gabungkan tabel anilist_data dan nonton berdasarkan anime_id
            jadwal_entries = (
                session.query(distinct(AnilistData.judul), Nonton.episode_number, AnilistData.anime_id)
                .join(Jadwal, Jadwal.anime_id == AnilistData.anime_id)
                .join(subquery, subquery.c.anime_id == AnilistData.anime_id)
                .outerjoin(Nonton, (subquery.c.anime_id == Nonton.anime_id) & (subquery.c.latest_episode == Nonton.episode_number))
                .filter(Jadwal.hari == user_input)
                .order_by(AnilistData.judul)
                .all()
            )

            response_text = f"Jadwal anime untuk hari {user_input}:\n"
            anime_keyboard = []

            for judul_anime, episode_number, anime_id in jadwal_entries:
                # Potong judul jika terlalu panjang
                if len(judul_anime) > 25:
                    judul_anime = judul_anime[:22] + "..."
                
                # Tambahkan informasi episode terbaru ke keyboard
                if episode_number is not None:
                    judul_anime += f" [{episode_number}]"

                anime_keyboard.append([f"{anime_id} {judul_anime}"])

                response_text += f"- Judul: {judul_anime} - Episode Terbaru: {episode_number}\n"
        finally:
            session.close()

        # Tambahkan tombol "Kembali"
        anime_keyboard.append(["Kembali"])

        # Bagi pesan menjadi beberapa bagian jika terlalu panjang
        max_message_length = 4096
        chunks = [response_text[i:i+max_message_length] for i in range(0, len(response_text), max_message_length)]

        for chunk in chunks:
            reply_markup = ReplyKeyboardMarkup(anime_keyboard, resize_keyboard=True)
            await message.reply_text(chunk, reply_markup=reply_markup)
            
    elif user_input == "kembali":
        # Jika pengguna memilih "Kembali", tampilkan kembali menu pilih hari
        keyboard = [
            ["Senin", "Selasa"],
            ["Rabu", "Kamis"],
            ["Jumat", "Sabtu"],
            ["Minggu"]
        ]

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await message.reply_text("Pilih hari:", reply_markup=reply_markup)

    elif user_input.startswith("upload"):
        parts = user_input.split()

    if len(parts) >= 4:
        anime_id = parts[1]
        episode_range = parts[2].split('-')
        start_episode = int(episode_range[0])
        end_episode = int(episode_range[1])
        video_info = parts[3:]

        # Validate that the number of video_info elements is even
        if len(video_info) % 2 == 0:
            session = SessionLocal()
            try:
                for episode_number in range(start_episode, end_episode + 1):
                    for i in range(0, len(video_info), 2):
                        video_url = f"{video_info[i]}{episode_number}"
                        resolusi = video_info[i + 1]

                        # Insert into the Nonton table for each pair of video_url and resolusi
                        new_nonton = Nonton(anime_id=anime_id, episode_number=episode_number, title=f"Episode {episode_number}", video_url=video_url, resolusi=resolusi)
                        session.add(new_nonton)
                        session.commit()

                await message.reply_text(f"Anime ID {anime_id}: Episodes {start_episode} to {end_episode} uploaded successfully!")
            finally:
                session.close()
        else:
            await message.reply_text("Invalid number of video URLs and resolutions. Each video URL must have a corresponding resolution.")
    else:
        await message.reply_text("Invalid upload command format. Use: 'upload <anime_id> <start_episode-end_episode> <video_url1> <res1> <video_url2> <res2> ...'")
