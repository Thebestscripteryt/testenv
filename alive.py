import threading
from env_logger_bot import bot, BOT_TOKEN

def run_bot():
    bot.run(BOT_TOKEN)

if __name__ == "__main__":
    print("Starting web server...")

    threading.Thread(target=run_bot).start()

    app.run(host="0.0.0.0", port=10000)
