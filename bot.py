from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy import func, distinct
from sqlalchemy.orm import aliased
from firebase_admin import credentials, messaging, initialize_app
from datetime import datetime
import re
import httpx
import requests

# Import the database models
from database import Jadwal, AnilistData, Nonton, UsersWeb, SessionLocal, engine, Base

API_ID = "7120601"
API_HASH = "aebd45c2c14b36c2c91dec3cf5e8ee9a"
BOT_TOKEN = "1920905087:AAG_xCvsdjxVu8VUDt9s4JhD22ND-UIJttQ"

# Initialize Firebase Admin SDK
cred = credentials.Certificate("servis.json")
firebase_app = initialize_app(cred)

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

@app.on_message(filters.command("add"))
async def add_command(client, message):
    # Extract the anime_id from the message text
    parts = message.text.split()
    if len(parts) == 2:
        anime_id = parts[1]

        # Send a POST request to the specified URL with the anime_id using httpx
        url = "https://ccgnimex.my.id/v2/android/scrapping/index.php"
        data = {"anime_id": anime_id}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, data=data)
                if response.status_code == 200:
                    await message.reply_text(f"Anime ID {anime_id} added successfully!")
                else:
                    await message.reply_text(f"Failed to add Anime ID {anime_id}. Server returned status code {response.status_code}")
        except Exception as e:
            await message.reply_text(f"An error occurred: {str(e)}")
    else:
        await message.reply_text("Invalid command format. Use: '/add <anime_id>'")


@app.on_message(filters.command("jadwal") & filters.private)
async def jadwal_commands(client, message):
    command = message.text.split()[1].lower()
    user_id = message.from_user.id

    # Create a database session
    session = SessionLocal()

    if command == "add":
        # Parse command arguments
        try:
            hari = message.text.split()[2]
            anime_id = int(message.text.split()[3])
        except IndexError:
            await message.reply("Format: /jadwal add (hari) (anime_id)")
            session.close()  # Close the session
            return
        except ValueError:
            await message.reply("Anime ID must be a valid integer.")
            session.close()  # Close the session
            return

        try:
            # Add jadwal to database
            current_time = datetime.now().strftime("%H:%M:%S")
            new_jadwal = Jadwal(hari=hari, anime_id=anime_id, jam=current_time)
            session.add(new_jadwal)
            session.commit()
            await message.reply("Jadwal berhasil ditambahkan.")
        except Exception as e:
            session.rollback()  # Rollback the transaction if an error occurs
            await message.reply(f"Failed to add jadwal: {str(e)}")
        finally:
            session.close()  # Close the session

    elif command == "delete":
        # Parse command arguments
        try:
            anime_id = int(message.text.split()[2])
        except IndexError:
            await message.reply("Format: /jadwal delete (anime_id)")
            session.close()  # Close the session
            return
        except ValueError:
            await message.reply("Anime ID must be a valid integer.")
            session.close()  # Close the session
            return

        try:
            # Delete jadwal from database
            session.query(Jadwal).filter(Jadwal.anime_id == anime_id).delete()
            session.commit()
            await message.reply("Jadwal berhasil dihapus.")
        except Exception as e:
            session.rollback()  # Rollback the transaction if an error occurs
            await message.reply(f"Failed to delete jadwal: {str(e)}")
        finally:
            session.close()  # Close the session

    else:
        await message.reply("Perintah tidak valid.")
        session.close()  # Close the session

@app.on_message(filters.text)
async def text_handler(client, message):
    user_input = message.text.lower()

    if user_input.startswith("upload"):
        parts = user_input.split()

        if len(parts) >= 4:
            if parts[1] == "off":
                # Jika perintah "off", lakukan pengunggahan ke database tanpa notifikasi
                anime_id = parts[2]
                start_episode = int(parts[3].split('-')[0])
                end_episode = int(parts[3].split('-')[1])

                session = SessionLocal()
                try:
                    for episode_number in range(start_episode, end_episode + 1):
                        for i in range(0, len(parts[4:]), 2):
                            url_match = re.search(r'/(\d+)', parts[4 + i])
                            if url_match:
                                numerical_part = int(url_match.group(1))
                                video_url = f"{parts[4 + i][:url_match.start(1)]}{numerical_part + episode_number - start_episode}{parts[4 + i][url_match.end(1):]}"
                                resolusi = parts[5 + i]

                                # Insert into the Nonton table for each pair of video_url and resolusi
                                new_nonton = Nonton(anime_id=anime_id, episode_number=episode_number, title=f"Episode {episode_number}", video_url=video_url, resolusi=resolusi)
                                session.add(new_nonton)
                                session.commit()
                            else:
                                await message.reply_text(f"Failed to extract numerical part from the video URL: {parts[4 + i]}")
                                return

                    if start_episode == end_episode:
                        await message.reply_text(f"Anime ID {anime_id}: Episode {start_episode} uploaded successfully!")
                    else:
                        await message.reply_text(f"Anime ID {anime_id}: Episodes {start_episode} to {end_episode} uploaded successfully!")

                finally:
                    session.close()
            else:
                # Jika bukan perintah "off", lakukan pengunggahan ke database dan kirim notifikasi
                anime_id = parts[1]
                start_episode = int(parts[2].split('-')[0])
                end_episode = int(parts[2].split('-')[1])

                session = SessionLocal()
                try:
                    for episode_number in range(start_episode, end_episode + 1):
                        for i in range(0, len(parts[3:]), 2):
                            url_match = re.search(r'/(\d+)', parts[3 + i])
                            if url_match:
                                numerical_part = int(url_match.group(1))
                                video_url = f"{parts[3 + i][:url_match.start(1)]}{numerical_part + episode_number - start_episode}{parts[3 + i][url_match.end(1):]}"
                                resolusi = parts[4 + i]

                                # Insert into the Nonton table for each pair of video_url and resolusi
                                new_nonton = Nonton(anime_id=anime_id, episode_number=episode_number, title=f"Episode {episode_number}", video_url=video_url, resolusi=resolusi)
                                session.add(new_nonton)
                                session.commit()
                            else:
                                await message.reply_text(f"Failed to extract numerical part from the video URL: {parts[3 + i]}")
                                return

                    # Kirim notifikasi
                    send_fcm_notifications(anime_id, start_episode, end_episode)

                    if start_episode == end_episode:
                        await message.reply_text(f"Anime ID {anime_id}: Episode {start_episode} uploaded successfully!")
                    else:
                        await message.reply_text(f"Anime ID {anime_id}: Episodes {start_episode} to {end_episode} uploaded successfully!")

                finally:
                    session.close()
        else:
            await message.reply_text("Invalid upload command format. Use: 'upload <anime_id> <start_episode-end_episode> <video_url1> <res1> <video_url2> <res2> ...'")

def send_fcm_notifications(anime_id, start_episode, end_episode=None):
    session = SessionLocal()
    try:
        # Ambil semua token FCM dari tabel users_web
        fcm_tokens = [str(token[0]) for token in session.query(UsersWeb.fcm_token).all()]

        # Ambil judul dan link gambar anime dari AnilistData berdasarkan anime_id
        anime_data = session.query(AnilistData.judul, AnilistData.image).filter(AnilistData.anime_id == anime_id).first()
        if anime_data:
            judul = anime_data.judul
            image_url = anime_data.image if anime_data.image else None
        else:
            judul = f"Anime ID {anime_id}"
            image_url = None

        # Persiapkan pesan notifikasi
        if start_episode == end_episode or end_episode is None:
            notification_body = f"{judul}: Episode {start_episode}"
        else:
            notification_body = f"{judul}: Episode {start_episode}-{end_episode}"

        # Buat objek notifikasi
        notification = messaging.Notification(
            title="Update Terbaru!!",
            body=notification_body,
        )

        # Tambahkan link gambar jika tersedia
        if image_url:
            notification.image = image_url

        # Maksimal 500 token FCM per pesan multicast
        max_tokens_per_message = 500
        total_tokens = len(fcm_tokens)

        for i in range(0, total_tokens, max_tokens_per_message):
            # Bagi daftar token menjadi batch
            tokens_batch = fcm_tokens[i:i + max_tokens_per_message]

            # Buat pesan multicast
            message = messaging.MulticastMessage(
                tokens=tokens_batch,
                notification=notification,
            )

            # Kirim pesan multicast
            response = messaging.send_multicast(message)
            print(f"Pemberitahuan FCM berhasil dikirim ke {len(tokens_batch)} pengguna.")

    except Exception as e:
        print(f"Error mengirim pemberitahuan FCM: {e}")
    finally:
        session.close()
