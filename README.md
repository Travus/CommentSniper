# Comment Sniper

Comment Sniper is a way to scan whole comment sections for comments and replies. It uses Discord as a user interface to take commands and give responses and is designed to be used by YouTube channel moderators or owners to check comment sections for offensive behavior, trouble users, spoilers, or similar. The bot is meant to work with comment sections up to a couple thousand comments, though it slows down significantly when approaching the 10 thousand mark due to all the requests to YouTube needed. It should handle videos with just a few thousand comments within a few seconds, though that also depends on your connection.
*It is not recommended to give normal users access to the bot. Discord and YouTube API constraints make this ill-advisable. Restrict this by blocking the bot out of public channels via Discord permissions.*

### Features

  - Searching by user
  - Searching for a specific text/word
  - Searching for a list of different texts/words
  - Saving custom named lists of texts/words to search with

&nbsp;
&nbsp;

### Usage
Once the bot is properly set up and has joined a Discord server it is ready to receive and execute commands to scan comment sections. In order to scan a comment section, you will need the video's ID. Video IDs can easily be found in the video URL, starting after `v=` and ending before the first following `&` sign, if there is one.

`!help` & `!help custom`
Help commands that show information on regular commands and commands associated with custom searches respectively.

`!toggledelete <on/off>`
Toggles whether the command messages should be deleted once detected by the bot or not. Remembers setting per server. If no value is set on a server it will not remove the commands per default. Changing this setting requires the `Manage Server` permission on the server.

`!usersearch <videoId> <user>`
Searches the video's comment section for comments and replies made by the user with the specified name. The username is not case sensitive. Returns links to all comments or replies that match the search, and notes if they are comments or replies.

`!phrasesearch <videoId> <phrase>`
Searches the video's comment section for comments and replies that contain a certain phrase. A phrase is not case sensitive and can be any text or word of 80 characters or shorter. Returns links to all comments or replies that match the search, and notes if they are comments or replies.

`!listsearch <videoId> <term1||term2||term3||...>`
Functions identical to the phrase search, except it takes a `||` (Two pipe symbols.) separated list of phrases and returns results matching at least one of the phrases in the list. Results note which term they matched with in addition to if it is a comment or a reply. If multiple terms match, it will display the first one that matched, no duplicated will be shown.

`!customsearch <videoId> <searchName>`
Functions identical to a list search, except it uses the terms saved to the custom search as terms rather than asking the user for them. This is intended to be used for frequent terms to spare users the need to save the list search elsewhere and enables multiple users to execute the same search without having to share their terms.

`!customsearches list`
Lists the names of all the custom searches that have been created on the server.

`!customsearches list <searchName>`
Lists all the terms saved in the specified search.

`!customsearches new <searchName>`
Creates a new custom search. No two custom searches on the same server can share the same name, furthermore, names are not case sensitive and can not be longer than 30 characters. There is a maximum of 50 custom searches per server. New custom searches have no terms saved to them.

`!customsearches delete <searchName>`
Deletes the specified custom search along with any terms that were saved to it.

`!customsearches addterm <searchName> <term>`
Saves a search term to the specified custom search. Search terms are not case sensitive and can be no longer than 80 characters.

`!customsearches removeterm <searchName> <term>`
Removes a searchterm from the spesified custom search.

### Prerequisites

Comment Sniper requires [Python 3.6](https://www.python.org/) or above aswell as [discord.py rewrite 1.0.0a](https://github.com/Rapptz/discord.py/tree/rewrite) by Rapptz.
To install the correct version of discord.py use:
```
pip install -U git+https://github.com/Rapptz/discord.py@rewrite#egg=discord.py
```

### Installation
Once you have the prerequisites, download the code from the repository and put `main.py` in the directory you want to run the program from. You can now run the file with Python and should receive an error due to missing credentials. The bot should now have created a new folder `credentials` with a file `youtube_key.txt` in it.

In order to proceed head over to the [Google Developer Console](https://console.developers.google.com) and create a project there. Enable the YouTube Data API v3 in the library tab and create an API key for the project in the credentials tab. Free users get about 12 or so free projects and the YouTube Data API v3 will have more than enough free quota every day for the purposes of this. You can now put the API key you created into the `youtube_key.txt` file the bot has created.

Now run `main.py` again. The bot will still complain about missing credentials and create a new file `discord_token.txt` next to the other one. In order to get a Discord token, head over to the [Discord Developer Portal](https://discordapp.com/developers/applications/), and log in if needed. From here create a new "application" as it is called, and on the bot tab, turn it into a Discord bot. Fill in any info you want and finally reveal your Discord token and put it into the `discord_token.txt` file. You can now run `main.py` again, and if you did everything up until now correctly you should not get an error anymore.

Optionally, if you want to change the command prefix from `!` to something else, open `main.py` in a text editor of your choosing, around the center of the file (line 244) you will find the line below, here you can change the prefix. This will not change the help commands and similar, however. If there is demand for a better way to do this, let me know and I can implement that pretty easily.
```
bot = commands.Bot(command_prefix="!")  # Set command prefix.
```

&nbsp;
You can now generate a bot invitation link to invite your newly created Discord bot to your server with [this website](https://discordapi.com/permissions.html). Simply check the permissions you need and give it your bot's client ID from its general information page in the developer portal. *(Not the token, don't ever share your token, that would let others take control of your bot!)* Alternatively you can also use the invite below and just add the client ID where it says `INSERT_CLIENT_ID_HERE`.
```
https://discordapp.com/oauth2/authorize?client_id=INSERT_CLIENT_ID_HERE&scope=bot&permissions=93184
```

### Contact

If you have any questions, needs or requests, feel free to contact me!
I'm mostly active on Discord, but I also have a Twitter.

Travus#8888 on Discord.
[@RealTravus](https://twitter.com/RealTravus) on Twitter
