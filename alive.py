"""
ALIVE.PY - Keep-alive server for Render
Starts web server on thread to keep service alive, then runs the bot
"""

from flask import Flask, jsonify
from threading import Thread
import logging
import os
import sys

# Suppress Flask logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

@app.route('/')
def home():
    return """
    <html>
        <head><title>Env Logger Bot</title></head>
        <body style="font-family: monospace; background: #1a1a2e; color: #eee; text-align: center; padding: 50px;">
            <h1>🔍 ENV LOGGER BOT</h1>
            <p>Status: <span style="color: #0f0;">ONLINE</span></p>
            <p>Discord Bot is running and capturing obfuscated sources</p>
            <hr>
            <p><small>Running on Render Web Service</small></p>
        </body>
    </html>
    """

@app.route('/health')
def health():
    return jsonify({
        "status": "alive",
        "service": "env-logger-bot",
        "timestamp": __import__('time').time()
    }), 200

@app.route('/ping')
def ping():
    return "pong", 200

def run_web_server():
    """Run Flask web server"""
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)

def start_bot():
    """Import and start the Discord bot"""
    print("[ALIVE] Starting Env Logger Bot...")
    
    # Add current directory to path for imports
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Import the bot module - this will start it
    try:
        import env_logger_bot
        print("[ALIVE] Bot module loaded successfully")
    except Exception as e:
        print(f"[ALIVE] Error loading bot: {e}")
        raise

def main():
    """Main entry point"""
    print("=" * 50)
    print("ENV LOGGER BOT - Render Deployment")
    print("=" * 50)
    
    # Start web server in background thread
    print("[ALIVE] Starting keep-alive web server...")
    web_thread = Thread(target=run_web_server, daemon=True)
    web_thread.start()
    print(f"[ALIVE] Web server running on port {os.environ.get('PORT', 10000)}")
    
    # Give web server time to start
    import time
    time.sleep(1)
    
    # Start the bot (blocking call)
    try:
        start_bot()
    except KeyboardInterrupt:
        print("\n[ALIVE] Shutting down...")
    except Exception as e:
        print(f"[ALIVE] Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()
