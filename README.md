Twitch Song Request Bot By MarshalLaw
A simple yet powerful Python-based Twitch chat bot that allows viewers to request songs, managed via a real-time web interface and displayable directly on your stream via OBS.

✨ Features
Twitch Chat Integration: Listen for song requests directly in your Twitch chat.

Web-Based Queue Management: Accept, deny, or remove songs from the queue through an intuitive web interface.

Real-time Queue Display: A dedicated HTML page for OBS Browser Source to show the live song queue on your stream.

Customizable Theme: Adjust colors, fonts, and sizes of the queue display via a web configuration panel.

Customizable Bot Responses: Tailor bot messages for various commands and scenarios directly from the web UI.

Persistent Queue: Song requests are saved to a local file (song_queue.json) and persist even if the bot is restarted.

Easy Setup: Designed to be straightforward to set up, even for users new to Python.

🚀 Getting Started
This section will guide you through getting the bot up and running. For a detailed, step-by-step tutorial including screenshots and common troubleshooting, please refer to the comprehensive Tutorial HTML file included in this repository.

Prerequisites
Before you begin, ensure you have:

Python 3.x: Download from python.org.

Important for Windows: During installation, ensure "Add Python X.Y to PATH" is checked.

A Text Editor: Such as Visual Studio Code, Notepad++, Sublime Text, or Atom.

OBS Studio (or similar streaming software) for displaying the queue on your stream.

📥 Get The Bot Files
Ensure you have all the following files in the same directory on your computer:

song_request_bot.py

config.json

default_config.json

song_queue.html

config.html

tutorial.html (this tutorial itself!)

🤖 Twitch Bot Account Setup
It is highly recommended to create a separate Twitch account for your bot.

Go to Twitch Sign Up and create a new account.

Log into this new bot account once.

In your main Twitch channel's chat, type: /mod yourbotnickname (replace yourbotnickname with your bot's Twitch username).

🔑 Get Your Twitch OAuth Token
Your bot needs a special token to connect to Twitch chat.

CRITICAL: Log into your Twitch bot account (NOT your main streamer account) in your web browser.

Go to Twitch Token Generator.

Click the button to generate a "Bot Chat Token".

Authorize the application when prompted.

Copy the entire token string, which will start with oauth:.

⚙️ Initial Configuration (config.json)
This is the only file you need to manually edit initially.

Open config.json in your text editor.

Update the following placeholders with your information:

"BOT_TOKEN": "oauth:YOUR_BOT_TOKEN_HERE": Paste your OAuth token here.

"CHANNEL": "your_channel_name_here": Your main Twitch channel name (all lowercase).

"BOT_NICK": "your_bot_nickname_here": Your bot's Twitch username (all lowercase).

Save the config.json file.

▶️ Run The Bot
Open Command Prompt (Windows) / Terminal (macOS/Linux).

Navigate to the bot's folder using the cd command.

Example: cd C:\Your\Bot\Folder\

Install Python Dependencies:

pip install twitchio

Run the Python Script:

python song_request_bot.py

Keep this window open while you want the bot to be running.

🌐 Web Interfaces
While the bot is running, you can access two local web interfaces in your browser:

Song Queue Display: http://localhost:8000/song_queue.html

This is the page you'll use for your OBS overlay.

Bot Configuration Page: http://localhost:8000/config.html

Use this to customize your bot's settings and appearance.

🎨 Configure Bot (Web UI)
Access http://localhost:8000/config.html to adjust your bot's behavior and UI:

Bot Settings: View connection details, and toggle song requests ON/OFF.

Note: Changes to BOT_TOKEN, CHANNEL, or BOT_NICK require a bot restart.

Theme & UI Colors: Customize fonts, sizes, and colors for the song_queue.html display. Includes a "Load Default Colors" button.

Bot Responses: Edit the messages your bot sends in chat. Supports placeholders like @{author_name}, {song}, etc. Includes a "Load Default Bot Speak" button.

Saving Changes: Click "Save Configuration" after making edits. "Reset Configuration" reverts unsaved changes on the page.

🎶 Manage Songs (Web UI)
The http://localhost:8000/song_queue.html page is your real-time queue manager:

Toggle Song Requests: Click the prominent ON/OFF button to enable/disable requests.

Song Queue Display: Shows all requested songs with status, requester, and time.

Action Buttons: Each song has buttons to Accept, Deny, or Remove it from the queue. Changes update instantly.

📺 OBS Browser Source Setup
Integrate your live song queue into your stream:

In OBS Studio, in the "Sources" dock, click + -> Browser.

Select "Create new" and name it (e.g., "Song Queue Display").

URL: Enter http://localhost:8000/song_queue.html

Width/Height: Adjust as needed (e.g., 500x1080).

Check "Shutdown source when not visible" and "Refresh browser when scene becomes active".

To interact with the queue in OBS (e.g., click Accept/Deny), right-click the source in your scene and select "Interact".

💬 Twitch Chat Commands
Your viewers can use these commands (customizable in config.html):

!sr <song name> by <artist> or !sr <song name> - <artist>: Request a song.

!remove: Removes the requester's most recent pending song.

!edit <new song name> by <new artist> or !edit <new song name> - <new artist>: Edits requester's most recent pending song.

!current: Shows the current song in the queue.

!pos: Shows requester's position in the queue.

!skip: Allows requester to skip their own song.

⚙️ Troubleshooting
Join the discord for support and lots of goodies related to Rocksmith https://discord.gg/BFfFVdTpxm
