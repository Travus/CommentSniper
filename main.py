# CommentSniper created by Travus on Dec. 12th 2018

from os import mkdir, path  # For checking if key files exists.
from sys import exit  # For graceful shutdown if crucial exception raised.
from urllib import request, error as urllib_error  # For interacting with YouTube API.
from concurrent import futures  # For asynchronous API requests.
import discord  # For using Discord as a user interface.
from discord.ext import commands  # For using Discord as a user interface.
import json  # For handling responses from the YouTube API.
from datetime import datetime  # Used for error logging.
import sqlite3  # Used to store special searches.
from aiohttp import ClientConnectorError as CCError  # To detect connection errors.


class Comment:
    """Container for info about comment or reply, with potential list of replies if comment."""

    def __init__(self, comment_id, vid_id, author, message, is_reply=False, replies=0):
        """Initialization of comment class."""
        self.id = comment_id
        self.vidId = vid_id
        self.author = author
        self.message = message
        if is_reply:
            self.kind = "reply"
        else:
            self.kind = "comment"
            self.replies = []
            self.replyAmount = replies

    def __repr__(self):
        """Debug representation of comment class."""
        return f"id: {self.id}\nkind: {self.kind}\nurl: <https://www.youtube.com/watch?v={self.vidId}&lc={self.id}>\nauthor: {self.author}\nmessage: {self.message}"

    def __str__(self):
        """String representation of comment class."""
        return f"<https://www.youtube.com/watch?v={self.vidId}&lc={self.id}> ({self.kind})"


def cur_time():
    """Returns current date and time."""
    return str(datetime.utcnow())[0:16]


def get_key(key_type):
    """Imports a Discord token or YouTube key from file."""
    directory = None
    try:
        if key_type == "discord":
            key_type = "Discord token"
            directory = "credentials/discord_token.txt"
        elif key_type == "youtube":
            key_type = "YouTube key"
            directory = "credentials/youtube_key.txt"
        key_file = open(directory, "r")
        key = str(key_file.read().strip())
        key_file.close()
        if len(key) == 0:
            raise FileNotFoundError
        else:
            return key
    except FileNotFoundError:
        if not path.isdir("credentials"):
            mkdir("credentials")
        key_file = open(directory, "w")
        key_file.close()
        print(f"[{cur_time()}] Error: Credentials not found. Place {key_type} in {directory}")
        exit(1)


async def get_comments(video_id, comments, page_token=None):
    """Populates 'comments' attribute (list) with comments and their replies."""
    page_token = "" if page_token is None else f"&pageToken={page_token}"
    request_url = f"https://www.googleapis.com/youtube/v3/commentThreads?key={ytKey}&part=snippet&maxResults=100&videoId={video_id}{page_token}"
    with request.urlopen(request_url) as req_url:
        response = req_url.read()
    response = json.loads(response)
    for comment in response['items']:
        comments.append(Comment(comment['id'], video_id, comment['snippet']['topLevelComment']['snippet']['authorDisplayName'],
                                comment['snippet']['topLevelComment']['snippet']['textOriginal'], False, comment['snippet']['totalReplyCount']))
    if "nextPageToken" in response:
        await get_comments(video_id, comments, response['nextPageToken'])
    else:
        with futures.ThreadPoolExecutor() as executor:
            [executor.submit(get_replies, com) for com in comments if com.replyAmount > 0]


def get_replies(comment, page_token=None):
    """Used by 'getComments' function to find replies to top-level comments."""
    page_token = "" if page_token is None else f"&pageToken={page_token}"
    request_url = f"https://www.googleapis.com/youtube/v3/comments?key={ytKey}&part=snippet&maxResults=100&parentId={comment.id}{page_token}"
    with request.urlopen(request_url) as req_url:
        response = req_url.read()
    response = json.loads(response)
    for reply in response['items']:
        comment.replies.append(Comment(reply['id'], comment.vidId, reply['snippet']['authorDisplayName'], reply['snippet']['textOriginal'], True))
    if "nextPageToken" in response:
        get_replies(comment, response['nextPageToken'])


def filter_user(comments, user):
    """Returns list of comments and replies filtered by author name."""
    results = []
    for comment in comments:
        if comment.author.lower() == user.lower():
            results.append(comment)
        for reply in comment.replies:
            if reply.author.lower() == user.lower():
                results.append(reply)
    if not results:
        return None
    return results


def filter_phrase(comments, phrase):
    """Returns list of comments and replies filtered by substring."""
    results = []
    for comment in comments:
        if phrase.lower() in comment.message.lower():
            results.append(comment)
        for reply in comment.replies:
            if phrase.lower() in reply.message.lower():
                results.append(reply)
    if not results:
        return None
    return results


def list_filter(comments, phrases):
    """Returns nested lists of comments and replies filtered by multiple substrings and the corresponding substring."""
    results = []
    final = []
    for filterWord in phrases:
        part_results = filter_phrase(comments, filterWord)
        if part_results is not None:
            for part in part_results:
                if part not in results:
                    results.append(part)
                    final.append([part, " (" + str(filterWord) + ")"])
    if not results:
        return None
    return final


async def send_result_message(ctx, results, search):
    """Sends result messages grouped by 10 results per message."""
    n = 0
    message = f"Results for {search}:"
    if results is not None:
        for result in results:
            n += 1
            if isinstance(result, list):
                message += f"\n{n}) {str(result[0])}{result[1]}"
            else:
                message += f"\n{n}) {str(result)}"
            if n % 10 == 0:
                await send(ctx, message)
                message = ""
        if n % 10:
            await send(ctx, message)
    else:
        await send(ctx, f"No result matches the {search}.")


async def validate(ctx, video_id):
    """Validates if videoId is valid and request goes through."""
    request_url = f"https://www.googleapis.com/youtube/v3/videos?key={ytKey}&part=id&id={video_id}"
    try:
        with request.urlopen(request_url) as req_url:
            response = req_url.read()
        if json.loads(response)['pageInfo']['totalResults'] == 0:
            print(f"[{cur_time()}] {ctx.message.author.id}: Video not found. The supplied VideoID is invalid.")
            await send(ctx, "Video not found. The supplied VideoID is invalid.")
            return 0
        else:
            return 1
    except urllib_error.HTTPError as ex:
        if ex.code == 400:
            print(f"[{cur_time()}] {ctx.message.author.id}: Request failed. Daily YouTube quota likely exceeded.")
            await send(ctx, "Request failed. Daily YouTube quota likely exceeded.")
            return 0


async def send(ctx, message):
    """Sends a message and tries to handle connection issues."""
    try:
        await ctx.send(message)
    except CCError:
        try:
            await ctx.send(message)
        except CCError:
            print(f"[{cur_time()}] {ctx.message.author.id}: Encountered client connection error. Could not resend message.")
            await ctx.send("Client connection error. Failed to send and resend message. Please try again.")


async def del_command(msg):
    """Tries to delete a message based on server preferences, logs failures."""
    db.execute("SELECT * FROM serverSettings WHERE serverId = ? AND deleteMessages = 1", (msg.guild.id, ))
    if db.fetchone():
        try:
            await msg.message.delete()
        except discord.Forbidden:
            print(f"[{cur_time()}] {msg.message.author.id}: Bot does not have required permissions to delete message.")


def create_db():
    """Establishes database if it is not already set up."""
    db.execute("CREATE TABLE IF NOT EXISTS customSearches(serverId INTEGER NOT NULL, searchName TEXT NOT NULL , searchId INTEGER DEFAULT 0 NOT NULL, PRIMARY KEY (serverId, searchName))")
    db.execute("CREATE TABLE IF NOT EXISTS searchTerms(searchId INTEGER NOT NULL, term TEXT NOT NULL, PRIMARY KEY (searchId, term))")
    db.execute("CREATE TABLE IF NOT EXISTS serverSettings(serverId INTEGER NOT NULL PRIMARY KEY, deleteMessages INTEGER NOT NULL)")
    db.execute("CREATE TRIGGER IF NOT EXISTS setId AFTER INSERT ON customSearches BEGIN UPDATE customSearches SET searchId = (SELECT MAX(searchId) FROM customSearches) + 1 WHERE searchId = 0; END;")
    db.execute("CREATE TRIGGER IF NOT EXISTS delTerms AFTER DELETE ON customSearches BEGIN DELETE FROM searchTerms WHERE searchTerms.searchId = OLD.searchId; END;")


async def check_if_exists(ctx, target_search, target_term=None, error_on_search=None, error_on_term=None):
    """Verifies if search or term exists, returns search ID and handles error messages."""
    db.execute("SELECT searchId FROM customSearches WHERE serverId = ? AND searchName = ?", (ctx.guild.id, target_search.lower()))
    search_id = db.fetchone()
    if search_id is None:
        if error_on_search == 0:
            await send(ctx, "No custom search with this name exists on this server.")
        return False, None
    elif target_term is None:
        if error_on_search == 1:
            await send(ctx, "A custom search with this name already exists on this server.")
        return search_id[0], None
    else:
        db.execute("SELECT COUNT(*) FROM searchTerms WHERE searchId = ? AND term = ?", (search_id[0], target_term.lower()))
        if db.fetchone()[0]:
            if error_on_term == 1:
                await send(ctx, "The term is already part of the custom search.")
            return search_id[0], True
        else:
            if error_on_term == 0:
                await send(ctx, "No such term is part of this custom search.")
            return search_id[0], False


dbcon = sqlite3.connect("database.db")  # Create sqlite3 database connection (Creates database file if not found.)
db = dbcon.cursor()  # Create sqlite3 database cursor.
create_db()
ytKey = get_key("youtube")
dKey = get_key("discord")
bot = commands.Bot(command_prefix="!")  # Set command prefix.
bot.remove_command("help")  # Remove ugly inbuilt help command.


@bot.event
async def on_ready():
    """Logs when bot is up and running."""
    print(f"{bot.user.name} is ready!\n------------------------------")


@bot.command(name="help")
async def help_command(ctx, *, additional=None):
    """Help command describing syntax and usage."""
    if ctx.guild is not None:
        await del_command(ctx)
        if additional is None or additional.lower() != "custom":
            await send(ctx, """Info:
        This bot allows you to scan all the comments and replies of a YouTube video for specific users, phrases, or a list of phrases.
        You can find video IDs in the video URL. It starts after ``v=`` and ends before a ``&`` character, if there is one.
        An example of this would be ``https://www.youtube.com/watch?v=AAAAAA&list=BBBBBBBBBBBBBB`` where AAAAAA would be the ID.""")
            await send(ctx, """Commands:
        ``!usersearch <videoId> <userName>``          Search video for comments and replies made by specific user.
        ``!phrasesearch <videoId> <searchPhrase>``          Search video for comments and replies containing specific phrase.
        ``!listsearch <videoId> <term1::term2::term3::...>``          Search video for comments and replies in a || specific list.
        ``!toggledelete <on/off>``          Chooses whether the bot deletes commands or not. Requires manage server permission.
        
Use ``!help custom`` for info on custom searches.
        """)
        else:
            await send(ctx, """Custom search info:
        ``!customsearch <videoId> <searchName>``          Search video for comments and replies containing terms associated with a custom search.

        ``!customsearches list``          List all custom searches on the server.
        ``!customsearches list <name>``          List all terms associated with a custom search.
        ``!customsearches new <name>``          Create a new custom search. Requires manage server permission.
        ``!customsearches delete <name>``          Delete a custom search. Requires manage server permission.
        ``!customsearches addterm <name> <term>``          Add a term to a custom search. Requires manage server permission.
        ``!customsearches removeterm <name> <term>``          Remove a term from a custom search. Requires manage server permission.
            """)


@bot.command(name="toggledelete")
async def toggeldelete(ctx, state=None):
    """Toggle whether commands should be delete on execution or not."""
    if ctx.guild is not None:
        if state is None or state.lower() not in ["on", "off"]:
            await send(ctx, "Invalid syntax. Correct syntax is ``!toggledelete <on/off>``")
        else:
            state = (1 if state.lower() == "on" else 0)
            perms = ctx.message.author.permissions_in(ctx.message.channel)
            if perms.manage_guild:
                db.execute("SELECT * FROM serverSettings WHERE serverId = ?", (ctx.guild.id, ))
                if db.fetchone():
                    db.execute("UPDATE serverSettings SET deleteMessages = ? WHERE serverId = ?", (state, ctx.guild.id))
                else:
                    db.execute("INSERT INTO serverSettings(serverId, deleteMessages) VALUES (?, ?)", (ctx.guild.id, state))
                dbcon.commit()
                await send(ctx, "Server message deletion state set.")
            else:
                await send(ctx, "You need the ``manage server`` permission to change this bot's settings for this server.")
        await del_command(ctx)


@bot.command(name="customsearches")
async def customsearches(ctx, op=None, name=None, *, term=None):
    """List custom searches and terms saved to them. Add new and delete custom searches, and add or remove terms from them."""
    if ctx.guild:
        await del_command(ctx)
        perms = ctx.message.author.permissions_in(ctx.message.channel)
        if op is None or op.lower() not in ["list", "new", "delete", "addterm", "removeterm"]:
            await send(ctx, "Invalid syntax. Correct syntax is ``!customsearches <list/new/delete/addterm/removeterm> [name] [term]``")
        elif op.lower() == "list" and name is None:
            db.execute("SELECT searchname FROM customSearches WHERE serverId = ?", (ctx.guild.id, ))
            searches = [str(row[0]) for row in db.fetchall()]
            if searches:
                response = "List of custom searches on the server:"
                for item in searches:
                    response += "\n" + item
                await send(ctx, response)
            else:
                await send(ctx, "There are no custom searches on this server.")
        elif op.lower() == "list" and name is not None:
            results = await check_if_exists(ctx, name, None, 0)
            if results[0]:
                db.execute("SELECT term FROM searchTerms WHERE searchId = ?", (results[0], ))
                terms = [str(row[0]) for row in db.fetchall()]
                if terms:
                    n = 0
                    response = f"List of terms in {name.lower()}:"
                    for item in terms:
                        response += "\n" + item
                        n += 1
                        if n % 10 == 0:
                            await send(ctx, response)
                            response = ""
                    if n % 10:
                        await send(ctx, response)
                else:
                    await send(ctx, "No search terms are associated with this search.")
        elif op.lower() == "new" and perms.manage_guild:
            if name is None:
                await send(ctx, "Invalid syntax. Correct syntax is ``!customsearches new <name>``")
            elif len(name) > 30:
                await send(ctx, "Custom search cannot be be more than 30 characters long.")
            else:
                db.execute("SELECT COUNT(*) FROM customSearches WHERE serverId = ?", (ctx.guild.id, ))
                if db.fetchone()[0] < 50:
                    try:
                        db.execute("INSERT INTO customSearches(serverId, searchName) VALUES (?, ?)", (ctx.guild.id, name.lower()))
                        dbcon.commit()
                        await send(ctx, f"Custom search '{name.lower()}' successfully added.")
                    except sqlite3.IntegrityError:
                        await send(ctx, "A custom search with this name already exists on this server.")
                else:
                    await send(ctx, "Maximum amount of 50 custom searches per server reached.")
        elif op.lower() == "delete" and perms.manage_guild:
            if name is None:
                await send(ctx, "Invalid syntax. Correct syntax is ``!customsearches delete <name>``")
            else:
                results = await check_if_exists(ctx, name, None, 0, None)
                if results[0]:
                    db.execute("DELETE FROM customSearches WHERE serverId = ? AND searchName = ?", (ctx.guild.id, name.lower()))
                    dbcon.commit()
                    await send(ctx, f"Custom search '{name.lower()}' successfully deleted.")
        elif op.lower() == "addterm" and perms.manage_guild:
            if name is None or term is None:
                await send(ctx, "Invalid syntax. Correct syntax is ``!customsearches addterm <name> <term>``")
            elif len(name) <= 80:
                results = await check_if_exists(ctx, name, term, 0, 1)
                if results[0] and not results[1]:
                    db.execute("INSERT INTO searchTerms(searchId, term) VALUES (?, ?)", (results[0], term.lower()))
                    dbcon.commit()
                    await send(ctx, f"The term '{term.lower()}' was successfully added to the custom search.")
            else:
                await send(ctx, "Search terms cannot be more than 80 characters long.")
        elif op.lower() == "removeterm" and perms.manage_guild:
            if name is None or term is None:
                await send(ctx, "Invalid syntax. Correct syntax is ``!customsearches removeterm <name> <term>``")
            else:
                results = await check_if_exists(ctx, name, term, 0, 0)
                if results[0] and results[1]:
                    db.execute("DELETE FROM searchTerms WHERE searchId = ? AND term = ?", (results[0], term.lower()))
                    dbcon.commit()
                    await send(ctx, f"The term '{term.lower()}' was successfully removed from the custom search.")
        else:
            await send(ctx, "You need the ``manage server`` permission to change this bot's custom commands for this server.")


@bot.command(name="usersearch")
async def usersearch(ctx, video_id=None, *, user=None):
    """Search video for comments and replies by user."""
    if ctx.guild:
        await del_command(ctx)
        if video_id is None or user is None:
            await send(ctx, "Invalid syntax. Correct syntax is ``!usersearch <videoId> <userName>``.")
        elif await validate(ctx, video_id):
            if len(user) <= 80:
                comments = []
                await get_comments(video_id, comments)
                await send_result_message(ctx, filter_user(comments, user), f"user search '{user}'")
            else:
                await send(ctx, "user names cannot be more than 80 characters long.")


@bot.command(name="phrasesearch")
async def phrasesearch(ctx, video_id=None, *, phrase=None):
    """Search video for comments and replies by substring."""
    if ctx.guild:
        await del_command(ctx)
        if video_id is None or phrase is None:
            await send(ctx, "Invalid syntax. Correct syntax is ``!phrasesearch <videoId> <searchPhrase>``.")
        elif await validate(ctx, video_id):
            if len(phrase) <= 80:
                comments = []
                await get_comments(video_id, comments)
                await send_result_message(ctx, filter_phrase(comments, phrase), f"phrase search '{phrase}'")
            else:
                await send(ctx, "Search phrases cannot be more than 80 characters long.")


@bot.command(name="customsearch")
async def customsearch(ctx, video_id=None, search=None):
    """Search video for comments and replies for substrings saved to custom search."""
    if ctx.guild:
        await del_command(ctx)
        if video_id is None or search is None:
            await send(ctx, "Invalid syntax. Correct syntax is ``!customsearch <videoId> <searchName>``.")
        elif await validate(ctx, video_id):
            results = await check_if_exists(ctx, search, None, 0, None)
            if results[0]:
                db.execute("SELECT term FROM searchTerms WHERE searchId = ?", (results[0], ))
                results = [result[0] for result in reversed(db.fetchall())]
                if results:
                    comments = []
                    await get_comments(video_id, comments)
                    await send_result_message(ctx, list_filter(comments, results), f"custom search '{search}'")
                else:
                    await send(ctx, "The search has no search terms associated with it.")


@bot.command(name="listsearch")
async def listsearch(ctx, video_id=None, *, terms=None):
    """Search video for comments and replies by list of substrings."""
    if ctx.guild:
        await del_command(ctx)
        if video_id is None or terms is None:
            await send(ctx, "Invalid syntax. Correct syntax is ``!listsearch <videoId> <term1::term2::term3::...>``.")
        elif await validate(ctx, video_id):
            terms = [term for term in terms.split("::") if term not in ["", " "]]
            term_amount = len(terms)
            terms = [term for term in terms if len(term) <= 80]
            if term_amount > len(terms):
                await send(ctx, "Search-terms cannot be more than 80 characters long, too long terms have been removed from search.")
            if terms:
                comments = []
                await get_comments(video_id, comments)
                await send_result_message(ctx, list_filter(comments, terms), "list search")
            elif term_amount:
                await send(ctx, "No search terms left after removing search terms over 80 characters long.")
            else:
                await send(ctx, "Invalid syntax. Correct syntax is ``!listsearch <videoId> <term1::term2::term3::...>``.")


@bot.event
async def on_command_error(ctx, error):
    """Logs errors, mainly used to log invalid commands."""
    if ctx.guild:
        print(f"[{cur_time()}] {ctx.message.author.id}: {error}")


try:  # Make test YouTube request and run the bot.
    with request.urlopen(f"https://www.googleapis.com/youtube/v3/videos?key={ytKey}&part=id&id=IOzpF_xeOSw") as url:
        url.read()
    bot.run(dKey)
except urllib_error.HTTPError as e:  # YouTube request failed, likely invalid key. Graceful shutdown.
    if e.code == 400:
        print(f"[{cur_time()}] Error: Request failed. YouTube key is likely invalid.")
        exit(2)
    else:
        raise
except discord.errors.LoginFailure:  # Bot login failure, likely invalid token. Graceful shutdown.
    print(f"[{cur_time()}] Error: Login failed. Discord token is likely invalid.")
    exit(2)
finally:
    db.close()  # Close sqlite3 database cursor.
    dbcon.close()  # Close sqlite3 database connection.


# Error Codes:
# 1 - Missing credentials.
# 2 - Credentials likely invalid.
