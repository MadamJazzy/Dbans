from discord.ext import commands
from handlers.data import rethink as r
import discord
import logging
import traceback
import os
import aiohttp

logging.basicConfig(level=logging.WARNING)

class Bot(commands.Bot):
    """Represents a discord bot.

    This class is a subclass of discord.Client and as a result anything that you
    can do with a discord.Client you can do with this bot.

    This class also subclasses GroupMixin to provide the functionality to manage commands.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = aiohttp.ClientSession(loop=self.loop)
        self._last_exception = None
        self.allowed_users = [209219778206760961]
        self.logger = logging.getLogger(__name__)

    async def download(self, url, name) -> discord.File:
        async with self.session.get(url) as r:
            with open(name, 'wb') as f:
                f.write(await r.read())
        return discord.File(name)


    async def on_ready(self):
        """Called when the client is done preparing the data received from Discord.
        Usually after login is successful and the Bot.guilds and co. are filled up.
        """
        for module in os.listdir('./modules'):
            if module == "__init__.py" or module == "__pycache__":
                continue
            else:
                try:
                    module = "modules." + module.replace('.py', '')
                    self.load_extension(module)
                except Exception as e:
                    log = ("Exception in loading module '{}'\n"
                           "".format(module))
                    log += "".join(traceback.format_exception(type(e), e,
                                e.__traceback__))
                    print(log)

        game = discord.Game("!report to report | Merry Christmas~!")
        await self.change_presence(status=discord.Status.online, activity=game)
        print("Logged in as:")
        print(self.user)
        print(f"ID: {self.user.id}")
        print("Finished starting!")

    async def on_command_error(self, ctx, error):
        """An error handler that is called when an error
        is raised inside a command either through user input error,
        check failure, or an error in your own code."""

        if hasattr(ctx.command, 'on_error'):
            self.logger.warning(f"{ctx.command.qualified_name} errored."
                                "Leaving error handling to the command.")
            return

        error = getattr(error, 'original', error)
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.DisabledCommand):
            return
        elif isinstance(error, commands.errors.CheckFailure):
            return
        elif isinstance(error, discord.errors.NotFound):
            return
        else:
            log = ("Exception in command '{}'\n"
                   "".format(ctx.command.qualified_name))
            log += "".join(traceback.format_exception(type(error), error,
                                                      error.__traceback__))
            self.logger.warning(log)
            self._last_exception = log

    async def on_command_completion(self, ctx):
        """An event that is called when a command has completed its invocation.
        This event is called only if the command succeeded,
        i.e. all checks have passed and the user input it correctly.
        """

        self.logger.info(f"{ctx.author} ({ctx.author.id}): "
                         "successfully executed command "
                         f"{ctx.command.qualified_name}.")

    async def on_raw_reaction_add(self, payload):
        channel_id = payload.channel_id
        user_id = payload.user_id
        guild_id = payload.guild_id
        message_id = payload.message_id
        emoji = payload.emoji
        channel = discord.utils.get(self.get_all_channels(), id=channel_id)
        message = (await channel.get_message(message_id))
        guild = discord.utils.get(self.guilds, id=guild_id)
        user = discord.utils.get(guild.members, id=user_id)
        reports = (await r.find('users', 'reports'))
        votes = (await r.find('users', 'votes'))
        votestats = (await r.find('users', 'votestats'))
        if not str(message_id) in reports or user == self.user:
            return

        if emoji.name == "✅":
            if votes[str(message_id)].get(str(user_id)) is None:
                votes[str(message_id)][str(user_id)] = 'accept'
                await r.update('users', 'votes', votes)
                if votestats.get(str(user_id)) is None:
                    votestats[str(user_id)] = 1
                else:
                    votestats[str(user_id)] += 1
                await r.update('users', 'votestats', votestats)
                self.dispatch('vote_update', message, user, 'accept',)
            elif votes[str(message_id)][str(user_id)] == 'accept':
                return
            elif votes[str(message_id)][str(user.id)] == 'reject':
                votes[str(message_id)][str(user.id)] = 'accept'
                votes[str(message_id)]['rejects'] -= 1
                e = votes[str(message.id)]['authors'].get(str(user.id))
                votes[str(message.id)]['reasons'][e] -= 1
                await r.update('users', 'votes', votes)
                self.dispatch('vote_update', message, user, 'accept')
                return
        elif emoji.name == "❌":
            if votes[str(message.id)].get(str(user.id)) is None:
                votes[str(message.id)][str(user.id)] = 'reject'
                await r.update('users', 'votes', votes)
                if votestats.get(str(user_id)) is None:
                    votestats[str(user_id)] = 1
                else:
                    votestats[str(user_id)] += 1
                await r.update('users', 'votestats', votestats)
                self.dispatch('vote_update', message, user, 'reject')
            elif votes[str(message.id)][str(user.id)] == 'reject':
                return
            elif votes[str(message.id)][str(user.id)] == 'accept':
                votes[str(message.id)][str(user.id)] = 'reject'
                votes[str(message.id)]['votes'] -= 1
                await r.update('users', 'votes', votes)
                self.dispatch('vote_update', message, user, 'reject')
                return
