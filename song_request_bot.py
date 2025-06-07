import re
import html
import os
from datetime import datetime, timedelta
import threading
from http.server import HTTPServer, CGIHTTPRequestHandler
import webbrowser
import json
import time
from twitchio.ext import commands
from urllib.parse import urlparse, parse_qs

# --- Configuration Loading ---
CONFIG_FILE = "config.json"
DEFAULT_CONFIG_FILE = "default_config.json" # Add this line
bot_config = {}

def load_config():
    global bot_config
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            bot_config = json.load(f)
            # Ensure essential keys are present, even if not in old config.json
            if "theme" not in bot_config:
                bot_config["theme"] = {}
            if "command_responses" not in bot_config:
                bot_config["command_responses"] = {}
            if "SONG_REQUESTS_ENABLED" not in bot_config:
                bot_config["SONG_REQUESTS_ENABLED"] = False
    else:
        # If config.json doesn't exist, try to load from default_config.json
        default_data = {}
        if os.path.exists(DEFAULT_CONFIG_FILE):
            with open(DEFAULT_CONFIG_FILE, "r", encoding="utf-8") as f:
                default_data = json.load(f)
        
        # Merge with hardcoded initial defaults, prioritizing default_data
        bot_config = {
            "BOT_TOKEN": "oauth:YOUR_BOT_TOKEN_HERE", # REMEMBER TO REPLACE THIS!
            "CHANNEL": "your_channel_name_here",     # REMEMBER TO REPLACE THIS!
            "BOT_NICK": "your_bot_nickname_here",    # REMEMBER TO REPLACE THIS!",
            "SONG_REQUESTS_ENABLED": default_data.get("SONG_REQUESTS_ENABLED", False), # Default to off
            "theme": default_data.get("theme", {
                "font_family": "'Segoe UI', Arial, sans-serif",
                "font_size": "16",
                "header_bg": "#4b4848",
                "header_text_color": "#ffffff",
                "status_on_bg": "#37ff00",
                "status_off_bg": "#ff0000",
                "config_button_bg": "#0066eb",
                "queue_row_bg": "#000000",
                "pending_bg": "#000000",
                "accepted_bg": "#04ff00",
                "denied_bg": "#ff0000",
                "text_color": "#ffffff",
                "queue_num_color": "#ffffff",
                "requester_color": "#ffffff",
                "time_ago_color": "#ffffff",
                "accept_btn_bg": "#02971b",
                "deny_btn_bg": "#a30000",
                "remove_btn_bg": "#7a890b"
            }),
            "command_responses": default_data.get("command_responses", {
                "sr_disabled_message": "@{author_name} - Sorry, song requests are currently unavailable for non-subscribers.",
                "sr_globally_disabled_message": "@{author_name} - Song requests are currently disabled by the streamer.",
                "sr_no_args_message": "@{author_name} - Please use format: !sr songname by artistname OR !sr songname - artistname",
                "sr_invalid_format_message": "@{author_name} - Invalid format! Use: !sr songname by artistname OR !sr songname - artistname",
                "sr_success_message": "@{author_name} - Added '{song}' by {artist} to the queue!",
                "remove_success_message": "@{author_name} - Removed '{song}' by {artist} from the queue!",
                "remove_no_pending_message": "@{author_name} - No pending song requests found to remove!",
                "edit_no_args_message": "@{author_name} - Please use format: !edit songname by artistname OR !edit songname - artistname",
                "edit_invalid_format_message": "@{author_name} - Invalid edit format! Use: !edit songname by artistname OR !edit songname - artistname",
                "edit_success_message": "@{author_name} - Your request for '{old_song}' by {old_artist} has been updated to '{new_song}' by {new_artist}!",
                "edit_no_pending_message": "@{author_name} - You have no pending song requests to edit.",
                "current_no_songs_message": "The song queue is currently empty!",
                "current_song_message": "Currently: '{song}' by {artist} (Requested by {requester})",
                "pos_no_pending_message": "@{author_name} - You have no pending song requests in the queue.",
                "pos_message": "@{author_name} - Your top request '{song}' by {artist} is currently #{position} in the queue.",
                "skip_success_message": "@{author_name} - Your request for '{song}' by {artist} has been skipped!",
                "skip_next_song_message": "Next up: '{song}' by {artist} (Requested by {requester})",
                "skip_queue_empty_message": "The queue is now empty!",
                "skip_no_pending_message": "@{author_name} - You have no pending song requests to skip.",
                "accept_bot_message": "Up Next: {song} by {artist} requested by {requester}",
                "deny_bot_message": "{author_name} has denied {song} by {artist} requested by {requester}"
            })
        }
        # Save this new config to config.json for the first run
        save_config(bot_config)
    return bot_config

def save_config(config_data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)
    print("Saved configuration:", config_data)

load_config() # Load config at startup

# --- Bot Setup ---
# Your existing bot class
class Bot(commands.Bot):
    def __init__(self):
        # Ensure token and channel are not placeholders before attempting connection
        if not bot_config.get("BOT_TOKEN") or bot_config.get("BOT_TOKEN") == "oauth:YOUR_BOT_TOKEN_HERE":
            print("\nWARNING: BOT_TOKEN is not set or is a placeholder in config.json.")
            print("Please configure your bot token via http://localhost:8000/config.html and restart the script.\n")
            # Set a dummy token to prevent crashing, but the bot won't connect
            super().__init__(token="oauth:dummytoken", prefix='!', initial_channels=[])
            return

        if not bot_config.get("CHANNEL") or bot_config.get("CHANNEL") == "your_channel_name_here":
            print("\nWARNING: CHANNEL is not set or is a placeholder in config.json.")
            print("Please configure your channel name via http://localhost:8000/config.html and restart the script.\n")
            super().__init__(token=bot_config["BOT_TOKEN"], prefix='!', initial_channels=[])
            return

        super().__init__(
            token=bot_config["BOT_TOKEN"],
            client_id="YOUR_CLIENT_ID", # This isn't strictly needed for basic bot, but good practice
            nick=bot_config["BOT_NICK"],
            prefix="!",
            initial_channels=[bot_config["CHANNEL"]]
        )


    async def event_ready(self):
        print(f"Logged in as | {self.nick}")
        print(f"User ID is | {self.user_id}")
        print(f"Connected to channel | {bot_config['CHANNEL']}") # Use bot_config here

    async def event_message(self, message):
        if message.echo:
            return
        print(f"[{message.channel.name}] {message.author.name}: {message.content}")
        await self.handle_commands(message)

    def parse_song_request_args(self, message_content):
        """Parse song request in the format 'songname by artistname' or 'songname - artistname'"""
        message_content = message_content.strip()
        
        # Try splitting by " by " first (case-insensitive)
        parts = re.split(pattern=r'\s+by\s+', string=message_content, maxsplit=1, flags=re.IGNORECASE)
        
        if len(parts) != 2:
            # If "by" not found or not correctly separated, try splitting by " - "
            parts = message_content.split(' - ', 1)
        
        if len(parts) != 2:
            return None  # Invalid format if neither "by" nor " - " found or not correctly separated
        
        song_part = parts[0].strip()
        artist_part = parts[1].strip()
        
        if not song_part or not artist_part:
            return None  # Missing song or artist
        
        return {"song": song_part, "artist": artist_part}

    # --- Commands (Rest of your existing commands) ---
    @commands.command(name="sr", aliases=['SR', 'sR', 'Sr'])
    async def song_request(self, ctx):
        # Use bot_config for the enabled status
        if not bot_config.get("SONG_REQUESTS_ENABLED", False):
            if ctx.author.is_subscriber or ctx.author.is_mod or ctx.author.is_broadcaster:
                response = bot_config["command_responses"].get("sr_globally_disabled_message", "Song requests are currently disabled by the streamer.")
                await ctx.send(response.format(author_name=ctx.author.name))
            else:
                response = bot_config["command_responses"].get("sr_disabled_message", "Sorry, song requests are currently unavailable for non-subscribers.")
                await ctx.send(response.format(author_name=ctx.author.name))
            return

        command_args = ctx.message.content[len("!sr"):].strip()
        if not command_args:
            response = bot_config["command_responses"].get("sr_no_args_message", "Please use format: !sr songname by artistname OR !sr songname - artistname")
            await ctx.send(response.format(author_name=ctx.author.name))
            return

        song_data = self.parse_song_request_args(command_args)
        if song_data is None:
            response = bot_config["command_responses"].get("sr_invalid_format_message", "Invalid format! Use: !sr songname by artistname OR !sr songname - artistname")
            await ctx.send(response.format(author_name=ctx.author.name))
            return
        
        song_id = generate_song_id()
        song_queue[song_id] = {
            "id": song_id,
            "song": ' '.join(word.capitalize() for word in song_data["song"].split()),
            "artist": ' '.join(word.capitalize() for word in song_data["artist"].split()),
            "user": ctx.author.name.capitalize(), # Capitalize user's first letter
            "user_id": ctx.author.id,
            "status": "pending",
            "timestamp": datetime.now().isoformat()
        }
        save_song_queue()
        response = bot_config["command_responses"].get("sr_success_message", "Added '{song}' by {artist} to the queue!")
        await ctx.send(response.format(author_name=ctx.author.name, song=song_data['song'], artist=song_data['artist']))

    @commands.command(name="remove")
    async def remove_song(self, ctx):
        requester_id = ctx.author.id
        # Find all pending songs by the requester
        pending_songs = [s for s in song_queue.values() if s["user_id"] == requester_id and s["status"] == "pending"]

        if not pending_songs:
            response = bot_config["command_responses"].get("remove_no_pending_message", "No pending song requests found to remove!")
            await ctx.send(response.format(author_name=ctx.author.name))
            return

        # For simplicity, remove the first pending song found
        song_to_remove = pending_songs[0]
        del song_queue[song_to_remove["id"]]
        save_song_queue()
        response = bot_config["command_responses"].get("remove_success_message", "Removed '{song}' by {artist} from the queue!")
        await ctx.send(response.format(author_name=ctx.author.name, song=song_to_remove['song'], artist=song_to_remove['artist']))

    @commands.command(name="edit", aliases=['editrequest', 'editsong'])
    async def edit_song(self, ctx):
        requester_id = ctx.author.id
        command_args = ctx.message.content[len("!edit"):].strip()

        if not command_args:
            response = bot_config["command_responses"].get("edit_no_args_message", "Please use format: !edit songname by artistname OR !edit songname - artistname")
            await ctx.send(response.format(author_name=ctx.author.name))
            return

        parsed_new_song = self.parse_song_request_args(command_args)
        if parsed_new_song is None:
            response = bot_config["command_responses"].get("edit_invalid_format_message", "Invalid edit format! Use: !edit songname by artistname OR !edit songname - artistname")
            await ctx.send(response.format(author_name=ctx.author.name))
            return

        # Find the first pending song by the requester
        song_to_edit = None
        for s in song_queue.values():
            if s["user_id"] == requester_id and s["status"] == "pending":
                song_to_edit = s
                break

        if not song_to_edit:
            response = bot_config["command_responses"].get("edit_no_pending_message", "You have no pending song requests to edit.")
            await ctx.send(response.format(author_name=ctx.author.name))
            return

        old_song_title = song_to_edit["song"]
        old_artist_name = song_to_edit["artist"]

        song_to_edit["song"] = ' '.join(word.capitalize() for word in parsed_new_song["song"].split())
        song_to_edit["artist"] = ' '.join(word.capitalize() for word in parsed_new_song["artist"].split())
        song_to_edit["timestamp"] = datetime.now().isoformat() # Update timestamp on edit
        save_song_queue()

        response = bot_config["command_responses"].get("edit_success_message", "Your request for '{old_song}' by {old_artist} has been updated to '{new_song}' by {new_artist}!")
        await ctx.send(response.format(
            author_name=ctx.author.name,
            old_song=old_song_title,
            old_artist=old_artist_name,
            new_song=song_to_edit['song'],
            new_artist=song_to_edit['artist']
        ))

    @commands.command(name="current", aliases=['currentsong'])
    async def current_song(self, ctx):
        current_queue = get_current_queue()
        if not current_queue:
            response = bot_config["command_responses"].get("current_no_songs_message", "The song queue is currently empty!")
            await ctx.send(response)
            return

        first_song = current_queue[0]
        response = bot_config["command_responses"].get("current_song_message", "Currently: '{song}' by {artist} (Requested by {requester})")
        await ctx.send(response.format(
            song=first_song['song'],
            artist=first_song['artist'],
            requester=first_song['user']
        ))

    @commands.command(name="pos", aliases=['position'])
    async def song_position(self, ctx):
        requester_id = ctx.author.id
        current_queue = get_current_queue()

        pos_found = -1
        song_at_pos = None

        for i, song in enumerate(current_queue):
            if song["user_id"] == requester_id and song["status"] == "pending":
                pos_found = i + 1
                song_at_pos = song
                break

        if pos_found != -1 and song_at_pos:
            response = bot_config["command_responses"].get("pos_message", "Your top request '{song}' by {artist} is currently #{position} in the queue.")
            await ctx.send(response.format(
                author_name=ctx.author.name,
                song=song_at_pos['song'],
                artist=song_at_pos['artist'],
                position=pos_found
            ))
        else:
            response = bot_config["command_responses"].get("pos_no_pending_message", "@{author_name} - You have no pending song requests in the queue.")
            await ctx.send(response.format(author_name=ctx.author.name))

    @commands.command(name="skip", aliases=['skipsong'])
    async def skip_song(self, ctx):
        requester_id = ctx.author.id
        
        # Ensure only the requester can skip their own pending song
        song_to_skip = None
        for song_id, song in song_queue.items():
            if song["user_id"] == requester_id and song["status"] == "pending":
                song_to_skip = song
                break

        if not song_to_skip:
            response = bot_config["command_responses"].get("skip_no_pending_message", "@{author_name} - You have no pending song requests to skip.")
            await ctx.send(response.format(author_name=ctx.author.name))
            return

        del song_queue[song_to_skip["id"]]
        save_song_queue()

        response = bot_config["command_responses"].get("skip_success_message", "@{author_name} - Your request for '{song}' by {artist} has been skipped!")
        await ctx.send(response.format(
            author_name=ctx.author.name,
            song=song_to_skip['song'],
            artist=song_to_skip['artist']
        ))

        # Announce next song if available
        current_queue = get_current_queue()
        if current_queue:
            next_song = current_queue[0]
            response = bot_config["command_responses"].get("skip_next_song_message", "Next up: '{song}' by {artist} (Requested by {requester})")
            await ctx.send(response.format(
                song=next_song['song'],
                artist=next_song['artist'],
                requester=next_song['user']
            ))
        else:
            response = bot_config["command_responses"].get("skip_queue_empty_message", "The queue is now empty!")
            await ctx.send(response)


# --- Song Queue Management ---
song_queue = {}
SONG_QUEUE_FILE = "song_queue.json"

def load_song_queue():
    global song_queue
    if os.path.exists(SONG_QUEUE_FILE):
        with open(SONG_QUEUE_FILE, "r", encoding="utf-8") as f:
            song_queue = json.load(f)
            # Convert timestamp strings back to datetime objects if needed for sorting/age calculation
            for song_id, song_data in song_queue.items():
                song_data['timestamp'] = datetime.fromisoformat(song_data['timestamp'])
    else:
        song_queue = {}

def save_song_queue():
    with open(SONG_QUEUE_FILE, "w", encoding="utf-8") as f:
        # Convert datetime objects to string before saving
        serializable_queue = {k: {**v, 'timestamp': v['timestamp'].isoformat()} if isinstance(v['timestamp'], datetime) else v for k, v in song_queue.items()}
        json.dump(serializable_queue, f, indent=4)

def generate_song_id():
    return str(int(time.time() * 1000)) # Unique ID based on timestamp

def get_current_queue():
    # Filter for pending and accepted songs, and sort by timestamp
    filtered_queue = [s for s in song_queue.values() if s["status"] in ["pending", "accepted"]]
    # Ensure timestamps are datetime objects before sorting
    for s in filtered_queue:
        if isinstance(s['timestamp'], str):
            s['timestamp'] = datetime.fromisoformat(s['timestamp'])
    filtered_queue.sort(key=lambda x: x["timestamp"])
    return filtered_queue


load_song_queue() # Load song queue at startup

# --- Web Server ---
class CustomHandler(CGIHTTPRequestHandler):
    def __init__(self, *args, bot, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)

    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)

        print(f"Received GET request: {self.path}") # Debugging line

        if path == "/song_queue.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            with open("song_queue.html", "rb") as f:
                self.wfile.write(f.read())
        elif path == "/config.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            with open("config.html", "rb") as f:
                self.wfile.write(f.read())
        elif path == "/get_queue":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            queue_for_display = []
            for song in get_current_queue():
                age = (datetime.now() - song['timestamp']).total_seconds()
                queue_for_display.append({
                    "id": song["id"],
                    "song": html.escape(song["song"]),
                    "artist": html.escape(song["artist"]),
                    "user": html.escape(song["user"]),
                    "status": song["status"],
                    "age_seconds": int(age)
                })
            self.wfile.write(json.dumps({
                "queue": queue_for_display,
                "requests_enabled": bot_config.get("SONG_REQUESTS_ENABLED", False),
                "theme": bot_config.get("theme", {})
            }).encode("utf-8"))
        elif path == "/get_config":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            # Send a copy to prevent accidental modification outside save_config
            self.wfile.write(json.dumps(bot_config).encode("utf-8"))
        elif path == "/get_default_config": # NEW HANDLER FOR DEFAULT CONFIG
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            default_data = {}
            if os.path.exists(DEFAULT_CONFIG_FILE):
                with open(DEFAULT_CONFIG_FILE, "r", encoding="utf-8") as f:
                    default_data = json.load(f)
            else:
                # Fallback to hardcoded defaults if default_config.json is missing
                default_data = {
                    "theme": {
                        "font_family": "'Segoe UI', Arial, sans-serif",
                        "font_size": "16",
                        "header_bg": "#4b4848",
                        "header_text_color": "#ffffff",
                        "status_on_bg": "#37ff00",
                        "status_off_bg": "#ff0000",
                        "config_button_bg": "#0066eb",
                        "queue_row_bg": "#000000",
                        "pending_bg": "#000000",
                        "accepted_bg": "#04ff00",
                        "denied_bg": "#ff0000",
                        "text_color": "#ffffff",
                        "queue_num_color": "#ffffff",
                        "requester_color": "#ffffff",
                        "time_ago_color": "#ffffff",
                        "accept_btn_bg": "#02971b",
                        "deny_btn_bg": "#a30000",
                        "remove_btn_bg": "#7a890b"
                    },
                    "command_responses": {
                        "sr_disabled_message": "@{author_name} - Sorry, song requests are currently unavailable for non-subscribers.",
                        "sr_globally_disabled_message": "@{author_name} - Song requests are currently disabled by the streamer.",
                        "sr_no_args_message": "@{author_name} - Please use format: !sr songname by artistname OR !sr songname - artistname",
                        "sr_invalid_format_message": "@{author_name} - Invalid format! Use: !sr songname by artistname OR !sr songname - artistname",
                        "sr_success_message": "@{author_name} - Added '{song}' by {artist} to the queue!",
                        "remove_success_message": "@{author_name} - Removed '{song}' by {artist} from the queue!",
                        "remove_no_pending_message": "@{author_name} - No pending song requests found to remove!",
                        "edit_no_args_message": "@{author_name} - Please use format: !edit songname by artistname OR !edit songname - artistname",
                        "edit_invalid_format_message": "@{author_name} - Invalid edit format! Use: !edit songname by artistname OR !edit songname - artistname",
                        "edit_success_message": "@{author_name} - Your request for '{old_song}' by {old_artist} has been updated to '{new_song}' by {new_artist}!",
                        "edit_no_pending_message": "@{author_name} - You have no pending song requests to edit.",
                        "current_no_songs_message": "The song queue is currently empty!",
                        "current_song_message": "Currently: '{song}' by {artist} (Requested by {requester})",
                        "pos_no_pending_message": "@{author_name} - You have no pending song requests in the queue.",
                        "pos_message": "@{author_name} - Your top request '{song}' by {artist} is currently #{position} in the queue.",
                        "skip_success_message": "@{author_name} - Your request for '{song}' by {artist} has been skipped!",
                        "skip_next_song_message": "Next up: '{song}' by {artist} (Requested by {requester})",
                        "skip_queue_empty_message": "The queue is now empty!",
                        "skip_no_pending_message": "@{author_name} - You have no pending song requests to skip.",
                        "accept_bot_message": "Up Next: {song} by {artist} requested by {requester}",
                        "deny_bot_message": "{author_name} has denied {song} by {artist} requested by {requester}"
                    }
                }
            self.wfile.write(json.dumps(default_data).encode("utf-8"))
        elif path == "/toggle_requests":
            status = query_params.get("status", ["off"])[0]
            bot_config["SONG_REQUESTS_ENABLED"] = (status == "on")
            save_config(bot_config)
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": f"Song requests turned {status}.", "enabled": bot_config["SONG_REQUESTS_ENABLED"]}).encode("utf-8"))
        else:
            # Handle other files if they exist, or fall back to 404
            try:
                # Attempt to serve static files (like CSS, JS if you have any)
                # You might need to add specific MIME types for other file types
                if os.path.exists(self.path[1:]): # Check if the file exists in the current directory
                    self.send_response(200)
                    if self.path.endswith(".css"):
                        self.send_header("Content-type", "text/css")
                    elif self.path.endswith(".js"):
                        self.send_header("Content-type", "application/javascript")
                    else:
                        self.send_header("Content-type", "application/octet-stream") # Generic binary
                    self.end_headers()
                    with open(self.path[1:], "rb") as f:
                        self.wfile.write(f.read())
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b"404 Not Found")
            except Exception as e:
                print(f"Error serving static file: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"500 Internal Server Error")


    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        print(f"Received POST request: {self.path}") # Debugging line

        if path == "/update_song_status":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode("utf-8"))
            
            song_id = data.get("id")
            action = data.get("action")
            
            response_message = process_song_action(song_id, action, self.bot) # Pass bot instance
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"message": response_message}).encode("utf-8"))
        elif path == "/save_config":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            new_config = json.loads(post_data.decode("utf-8"))
            
            # Update only the parts that are configurable via the HTML page
            for key in ["BOT_TOKEN", "CHANNEL", "BOT_NICK"]:
                if key in new_config:
                    bot_config[key] = new_config[key]
            
            if "theme" in new_config and isinstance(new_config["theme"], dict):
                # Ensure theme key exists
                if "theme" not in bot_config:
                    bot_config["theme"] = {}
                for theme_key, theme_value in new_config["theme"].items():
                    bot_config["theme"][theme_key] = theme_value
            
            if "command_responses" in new_config and isinstance(new_config["command_responses"], dict):
                # Ensure command_responses key exists
                if "command_responses" not in bot_config:
                    bot_config["command_responses"] = {}
                for cmd_key, cmd_value in new_config["command_responses"].items():
                    bot_config["command_responses"][cmd_key] = cmd_value

            save_config(bot_config) # Save updated config to file
            
            # Re-generate song_queue.html immediately to apply new theme
            write_initial_html_file()

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"message": "Configuration saved successfully. Theme applied. Restart bot for token/channel changes."}).encode("utf-8"))
        else:
            self.send_error(404, "Not Found")

def process_song_action(song_id, action, bot): # Added bot parameter
    try:
        song_id = str(song_id)
        if song_id in song_queue:
            song = song_queue[song_id]
            if action == "accept":
                song_queue[song_id]["status"] = "accepted"
                print(f"Accepted song ID {song_id}: {song['song']}")
                bot.loop.create_task(bot.get_channel(bot_config["CHANNEL"]).send( # Use bot_config["CHANNEL"]
                    bot_config["command_responses"].get("accept_bot_message", "Up Next: {song} by {artist} requested by {requester}").format(
                        song=song['song'], artist=song['artist'], requester=song['user']
                    )
                ))
            elif action == "deny":
                song_queue[song_id]["status"] = "denied"
                print(f"Denied song ID {song_id}: {song['song']}")
                bot.loop.create_task(bot.get_channel(bot_config["CHANNEL"]).send( # Use bot_config["CHANNEL"]
                    bot_config["command_responses"].get("deny_bot_message", "{author_name} has denied {song} by {artist} requested by {requester}").format(
                        author_name=bot_config["BOT_NICK"], song=song['song'], artist=song['artist'], requester=song['user'] # Use BOT_NICK for author_name
                    )
                ))
            elif action == "remove":
                removed_song = song_queue.pop(song_id)
                print(f"Removed song ID {song_id}: {removed_song['song']}")
            save_song_queue() # Save changes to queue after action
            return "Action processed successfully"
        else:
            print(f"Invalid song ID: {song_id}")
            return "Invalid song ID"
    except ValueError:
        print(f"Invalid song ID value: {song_id}")
        return "Invalid request"

def format_time_ago(timestamp):
    now = datetime.now()
    diff = now - timestamp
    
    seconds = int(diff.total_seconds())
    
    if seconds < 60:
        return f"{seconds} second{'s' if seconds != 1 else ''} ago"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if remaining_seconds > 0:
            return f"{minutes} minute{'s' if minutes != 1 else ''} {remaining_seconds} second{'s' if remaining_seconds != 1 else ''} ago"
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes > 0:
            return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''} ago"
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = seconds // 86400
        return f"{days} day{'s' if days != 1 else ''} ago"

def write_initial_html_file():
    theme = bot_config.get("theme", {}) # Get theme settings
    
    # Generate dynamic CSS variables
    dynamic_css = f"""
        :root {{
            --font-family: {theme.get('font_family', "'Segoe UI', Arial, sans-serif")};
            --font-size: {theme.get('font_size', '16')}px;
            --header-bg: {theme.get('header_bg', 'rgba(30, 30, 30, 0.8)')};
            --header-text-color: {theme.get('header_text_color', '#fff')};
            --status-on-bg: {theme.get('status_on_bg', 'linear-gradient(145deg, #2ecc71, #27ae60)')};
            --status-off-bg: {theme.get('status_off_bg', 'linear-gradient(145deg, #e74c3c, #c0392b)')};
            --config-button-bg: {theme.get('config_button_bg', 'linear-gradient(145deg, #3498db, #2980b9)')};
            --queue-row-bg: {theme.get('queue_row_bg', 'rgba(50, 50, 50, 0.6)')};
            --pending-bg: {theme.get('pending_bg', 'rgba(0, 0, 0, 0.7)')};
            --accepted-bg: {theme.get('accepted_bg', 'rgba(40, 167, 69, 0.7)')};
            --denied-bg: {theme.get('denied_bg', 'rgba(220, 53, 69, 0.7)')};
            --text-color: {theme.get('text_color', '#e0e0e0')};
            --queue-num-color: {theme.get('queue_num_color', '#999')};
            --requester-color: {theme.get('requester_color', '#bbb')};
            --time-ago-color: {theme.get('time_ago_color', '#999')};
            --accept-btn-bg: {theme.get('accept_btn_bg', '#28a745')};
            --deny-btn-bg: {theme.get('deny_btn_bg', '#dc3545')};
            --remove-btn-bg: {theme.get('remove_btn_bg', '#ffc107')};
        }}
    """

    full_html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Song Request Queue</title>
    <style>
        {dynamic_css} /* Inject dynamic CSS variables here */

        body {{ 
            font-family: var(--font-family); 
            font-size: var(--font-size); /* Use font size */
            margin: 0; 
            background: transparent; /* Keep background transparent for OBS overlay */
            color: var(--text-color); 
            width: 450px; /* Increased width to accommodate new layout */
            overflow: hidden; /* Prevent scrollbars in OBS */
        }}
        .header-container {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 15px;
            background: var(--header-bg); 
            color: var(--header-text-color);
            font-size: 20px;
            font-weight: bold;
            border-bottom: 2px solid #00bfff; /* Thicker, distinct blue line */
        }}
        .status-button {{
            padding: 8px 15px; 
            border-radius: 20px; 
            font-size: 16px; 
            font-weight: bold;
            color: white;
            text-transform: uppercase;
            cursor: pointer;
            transition: all 0.3s ease; 
            box-shadow: 
                inset 0 2px 4px rgba(0,0,0,0.4), 
                inset 0 -2px 4px rgba(255,255,255,0.2), 
                0 2px 5px rgba(0,0,0,0.5); 
            border: 1px solid rgba(255,255,255,0.1); 
            text-shadow: 0 1px 2px rgba(0,0,0,0.6); 
            margin-left: 10px; 
        }}
        .status-on {{
            background: var(--status-on-bg); 
        }}
        .status-off {{
            background: var(--status-off-bg); 
        }}
        #config-button-container {{
            position: fixed; 
            top: 5px; 
            right: 5px; 
            background: rgba(0, 0, 0, 0.5); 
            padding: 3px;
            border-radius: 5px;
            z-index: 1000; 
        }}
        .configure-button {{
            padding: 3px 6px; 
            border-radius: 10px; 
            font-size: 10px; 
            font-weight: bold;
            color: white;
            background: var(--config-button-bg); 
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 
                inset 0 1px 2px rgba(0,0,0,0.4), 
                inset 0 -1px 2px rgba(255,255,255,0.2), 
                0 1px 3px rgba(0,0,0,0.5);
            border: 1px solid rgba(255,255,255,0.1);
            text-shadow: 0 0.5px 1px rgba(0,0,0,0.6);
            text-decoration: none; 
            display: block; 
        }}
        .configure-button:hover {{
            filter: brightness(1.1); /* Slightly brighten on hover for general gradient */
        }}
        #song-queue-container {{ 
            display: flex; 
            flex-direction: column;
            gap: 8px; 
            margin-top: 10px; 
        }}
        .song-row {{ 
            background: var(--queue-row-bg); 
            display: flex; 
            border-radius: 5px; 
            overflow: hidden; 
            position: relative; 
            padding: 8px 10px; 
            align-items: center; 
        }}
        /* Status colors for rows */
        .pending {{ background: var(--pending-bg); }} 
        .accepted {{ background: var(--accepted-bg); }} 
        .denied {{ background: var(--denied-bg); }} 

        .queue-number {{
            font-size: 12px;
            font-weight: bold;
            color: var(--queue-num-color);
            flex-shrink: 0; 
            margin-right: 10px; 
        }}

        .song-info-wrapper {{
            flex-grow: 1; 
            display: flex;
            flex-direction: column; 
        }}

        .song-title-artist-line {{
            display: flex;
            justify-content: space-between; 
            align-items: baseline; 
            font-size: 16px;
            font-weight: bold;
            line-height: 1.3;
        }}
        .song-title-artist-line span {{
            flex-shrink: 1; 
        }}
        .requester {{
            font-size: 13px;
            color: var(--requester-color); 
            margin-top: 2px;
            font-style: italic;
        }}
        .time-ago {{
            font-size: 11px;
            color: var(--time-ago-color);
            white-space: nowrap; 
            margin-left: 15px; 
            flex-shrink: 0; 
        }}
        .action-buttons-container {{
            display: flex;
            flex-direction: column; 
            gap: 2px; 
            margin-left: 15px; 
            flex-shrink: 0; 
        }}
        .action-btn {{ 
            padding: 3px 6px; 
            font-size: 12px; 
            cursor: pointer; 
            border: none; 
            border-radius: 4px; 
            transition: background 0.2s ease; 
            color: white; 
            line-height: 1; 
        }}
        .accept-btn {{ background: var(--accept-btn-bg); }} 
        .accept-btn:hover {{ filter: brightness(0.9); }}
        .deny-btn {{ background: var(--deny-btn-bg); }} 
        .deny-btn:hover {{ filter: brightness(0.9); }}
        .remove-btn {{ background: var(--remove-btn-bg); }} 
        .remove-btn:hover {{ filter: brightness(0.9); }}
    </style>
</head>
<body>
    <div class="header-container">
        <div>SONG REQUESTS</div>
        <div id="statusToggle" class="status-button"></div>
    </div>
    <div id="song-queue-container">
        </div>

    <div id="config-button-container">
        <a href="/config.html" class="configure-button">Config</a>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const songQueueContainer = document.getElementById('song-queue-container');
            const statusToggleButton = document.getElementById('statusToggle');
            let currentStatus = true; // Initial status, will be updated by server

            // Function to update the status button's display
            function updateStatusButtonDisplay(isEnabled) {{
                currentStatus = isEnabled;
                if (isEnabled) {{
                    statusToggleButton.classList.remove('status-off');
                    statusToggleButton.classList.add('status-on');
                    statusToggleButton.innerHTML = 'ON &#9835;';
                }} else {{
                    statusToggleButton.classList.remove('status-on');
                    statusToggleButton.classList.add('status-off');
                    statusToggleButton.innerHTML = 'OFF &#9835;';
                }}
            }}

            // Function to fetch and render the queue and status
            async function updateQueueDisplay() {{
                try {{
                    const queueResponse = await fetch('/get_queue'); // Updated to /get_queue
                    if (!queueResponse.ok) {{
                        throw new Error(`HTTP error! status: ${{queueResponse.status}}`);
                    }}
                    const data = await queueResponse.json(); // Read entire response as JSON
                    const queue = data.queue;
                    const requestsEnabled = data.requests_enabled; // Get enabled status from combined response
                    const theme = data.theme; // Get theme from combined response

                    // Apply theme directly (no need to fetch separately)
                    document.documentElement.style.setProperty('--font-family', theme.font_family);
                    document.documentElement.style.setProperty('--font-size', theme.font_size + 'px');
                    document.documentElement.style.setProperty('--header-bg', theme.header_bg);
                    document.documentElement.style.setProperty('--header-text-color', theme.header_text_color);
                    document.documentElement.style.setProperty('--status-on-bg', theme.status_on_bg);
                    document.documentElement.style.setProperty('--status-off-bg', theme.status_off_bg);
                    document.documentElement.style.setProperty('--config-button-bg', theme.config_button_bg);
                    document.documentElement.style.setProperty('--queue-row-bg', theme.queue_row_bg);
                    document.documentElement.style.setProperty('--pending-bg', theme.pending_bg);
                    document.documentElement.style.setProperty('--accepted-bg', theme.accepted_bg);
                    document.documentElement.style.setProperty('--denied-bg', theme.denied_bg);
                    document.documentElement.style.setProperty('--text-color', theme.text_color);
                    document.documentElement.style.setProperty('--queue-num-color', theme.queue_num_color);
                    document.documentElement.style.setProperty('--requester-color', theme.requester_color);
                    document.documentElement.style.setProperty('--time-ago-color', theme.time_ago_color);
                    document.documentElement.style.setProperty('--accept-btn-bg', theme.accept_btn_bg);
                    document.documentElement.style.setProperty('--deny-btn-bg', theme.deny_btn_bg);
                    document.documentElement.style.setProperty('--remove-btn-bg', theme.remove_btn_bg);

                    updateStatusButtonDisplay(requestsEnabled); // Update UI based on combined response

                    let htmlContent = '';
                    queue.forEach((song, index) => {{
                        const statusClass = song.status.toLowerCase();
                        htmlContent += `
                            <div class="song-row ${{statusClass}}">
                                <div class="queue-number">${{index + 1}}:</div>
                                <div class="song-info-wrapper">
                                    <div class="song-title-artist-line">
                                        <span>${{escapeHtml(song.song)}} - ${{escapeHtml(song.artist)}}</span>
                                        <span class="time-ago">${{formatTimeAgo(song.age_seconds)}}</span>
                                    </div>
                                    <div class="requester">by ${{escapeHtml(song.user)}}</div>
                                </div>
                                <div class="action-buttons-container">
                                    <button class="action-btn accept-btn" data-action="accept" data-id="${{song.id}}">&#10003;</button>
                                    <button class="action-btn deny-btn" data-action="deny" data-id="${{song.id}}">&#128711;</button>
                                    <button class="action-btn remove-btn" data-action="remove" data-id="${{song.id}}">&#10799;</button>
                                </div>
                            </div>
                        `;
                    }});
                    songQueueContainer.innerHTML = htmlContent;

                    // Reattach event listeners to new buttons
                    document.querySelectorAll('.action-btn').forEach(button => {{
                        button.onclick = function() {{
                            sendAction(this.dataset.action, this.dataset.id);
                        }};
                    }});

                }} catch (error) {{
                    console.error('Error fetching data:', error);
                }}
            }}

            // Function to send action to the server
            async function sendAction(action, id) {{
                try {{
                    const response = await fetch('/update_song_status', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{ id: id, action: action }})
                    }});
                    if (!response.ok) {{
                        throw new Error(`HTTP error! status: ${{response.status}}`);
                    }}
                    await updateQueueDisplay(); // Refresh queue after action
                }} catch (error) {{
                    console.error('Error sending action:', error);
                }}
            }}

            // Simple HTML escaping to prevent XSS
            function escapeHtml(text) {{
                var map = {{
                    '&': '&amp;',
                    '<': '&lt;',
                    '>': '&gt;',
                    '"': '&quot;',
                    "'": '&#039;'
                }};
                return text.replace(/[&<>"']/g, function(m) {{ return map[m]; }});
            }}

            function formatTimeAgo(seconds) {{
                if (seconds < 60) {{
                    return `${{seconds}} second${{seconds !== 1 ? 's' : ''}} ago`;
                }} else if (seconds < 3600) {{
                    const minutes = Math.floor(seconds / 60);
                    const remainingSeconds = seconds % 60;
                    if (remainingSeconds > 0) {{
                        return `${{minutes}} minute${{minutes !== 1 ? 's' : ''}} ${{remainingSeconds}} second${{remainingSeconds !== 1 ? 's' : ''}} ago`;
                    }}
                    return `${{minutes}} minute${{minutes !== 1 ? 's' : ''}} ago`;
                }} else if (seconds < 86400) {{
                    const hours = Math.floor(seconds / 3600);
                    const minutes = Math.floor((seconds % 3600) / 60);
                    if (minutes > 0) {{
                        return `${{hours}} hour${{hours !== 1 ? 's' : ''}} ${{minutes}} minute${{minutes !== 1 ? 's' : ''}} ago`;
                    }}
                    return `${{hours}} hour${{hours !== 1 ? 's' : ''}} ago`;
                }} else {{
                    const days = Math.floor(seconds / 86400);
                    return `${{days}} day${{days !== 1 ? 's' : ''}} ago`;
                }}
            }}

            // Toggle functionality for the ON/OFF button
            statusToggleButton.addEventListener('click', async function() {{
                // Send request to toggle status
                const newStatus = !currentStatus;
                try {{
                    const response = await fetch(`/toggle_requests?status=${{newStatus ? 'on' : 'off'}}`);
                    if (!response.ok) {{
                        throw new Error(`HTTP error! status: ${{response.status}}`);
                    }}
                    const result = await response.json();
                    updateStatusButtonDisplay(result.enabled); // Update UI based on server's response
                    updateQueueDisplay(); // Refresh queue (though not strictly necessary for status change)
                }} catch (error) {{
                    console.error('Error toggling status:', error);
                }}
            }});

            // Initial display and then update every 5 seconds
            updateQueueDisplay();
            setInterval(updateQueueDisplay, 5000); 
        }});
    </script>
</body>
</html>
"""
    with open("song_queue.html", "w", encoding="utf-8") as f:
        f.write(full_html_content)

def run_server(bot_instance): # Changed parameter name to avoid conflict
    server = HTTPServer(("", 8000), lambda *args, **kwargs: CustomHandler(*args, bot=bot_instance, **kwargs))
    print("Server started on port 8000")
    server.serve_forever()

if __name__ == "__main__":
    bot = Bot()

    # This ensures song_queue.html is created/updated with the Configure button
    write_initial_html_file() 
    
    server_thread = threading.Thread(target=run_server, args=(bot,)) # Pass bot instance
    server_thread.daemon = True
    server_thread.start()

    # Open the song_queue.html in a web browser
    webbrowser.open("http://localhost:8000/song_queue.html")

    # Start the bot
    bot.run()