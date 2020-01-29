import discord
import traceback
from discord.ext import commands
from handlers import checks


class Developer(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    async def __local_check(self, ctx):
        return ctx.author.id in ctx.bot.allowed_users

    def pagify(self, text, delims=["\n"], *, escape=True, shorten_by=8,
               page_len=1000):
        """DOES NOT RESPECT MARKDOWN BOXES OR INLINE CODE"""
        in_text = text
        if escape:
            num_mentions = text.count("@here") + text.count("@everyone")
            shorten_by += num_mentions
        page_len -= shorten_by
        while len(in_text) > page_len:
            closest_delim = max([in_text.rfind(d, 0, page_len)
                                 for d in delims])
            closest_delim = closest_delim if closest_delim != -1 else page_len
            if escape:
                to_send = self.escape_mass_mentions(in_text[:closest_delim])
            else:
                to_send = in_text[:closest_delim]
            yield to_send
            in_text = in_text[closest_delim:]

        if escape:
            yield self.escape_mass_mentions(in_text)
        else:
            yield in_text

    def box(self, text, lang=""):
        ret = f"```{lang}\n{text}\n```"
        return ret

    def escape(self, text, *, mass_mentions=False, formatting=False):
        if mass_mentions:
            text = text.replace("@everyone", "@\u200beveryone")
            text = text.replace("@here", "@\u200bhere")
        if formatting:
            text = (text.replace("`", "\\`")
                        .replace("*", "\\*")
                        .replace("_", "\\_")
                        .replace("~", "\\~"))
        return text

    def escape_mass_mentions(self, text):
        return self.escape(text, mass_mentions=True)

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    def get_syntax_error(self, e):
        if e.text is None:
            return f'```py\n{e.__class__.__name__}: {e}\n```'
        return f"""```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}:
        {e}```"""

    @commands.command()
    async def ping(self, ctx) -> discord.Message:
        """Pings the bot."""
        return await ctx.send(f"🏓 Pong. Time: {round(ctx.bot.latency*1000)}ms")

    @checks.is_dev()
    @commands.command()
    async def traceback(self, ctx, public: bool=None) -> discord.Message:
        """Sends to the owner the last command exception that has occurred
        If public (yes is specified), it will be sent to the chat instead"""
        if not public:
            destination = ctx.author
        else:
            destination = ctx.channel

        if self.bot._last_exception:
            return await destination.send("```py\n"+ctx.bot._last_exception+"\n```")
        else:
            return await destination.send("No exception has occured yet!")

    @checks.is_dev()
    @commands.command()
    async def load(self, ctx, module: str) -> discord.Message:
        """Loads cogs/modules from the bot."""
        if 'modules.' not in module:
            ext = "modules." + module
        try:
            ctx.bot.load_extension(ext)
            await ctx.send("The module has successfully been loaded.")
        except ModuleNotFoundError:
            return await ctx.send("I couldn't find that module.")
        except Exception as e:
            error = ("Exception in loading module '{}'\n"
              "".format(module))
            error += "".join(traceback.format_exception(type(e), e,
                            e.__traceback__))
            self._cog_error = error
            try:
                await ctx.author.send("```py\n"+error+"\n```")
            except discord.errors.Forbidden:
                return await ctx.send("Module was found and possibly loaded, but "
                                      "something went wrong. "
                                      "Check your console "
                                      "for more information.")
            return await ctx.send("Module was found and possibly loaded, but "
                                 "something went wrong. "
                                 "I've sent you more information in DMs.")

    @checks.is_dev()
    @commands.command()
    async def unload(self, ctx, module: str) -> discord.Message:
        """Unloads cogs/modules from the bot."""
        if 'modules.' not in module:
            module = "modules." + module
        ctx.bot.unload_extension(module)
        module = module.replace('modules.', '')
        return await ctx.send(f"Successfully unloaded that module.")

    @checks.is_dev()
    @commands.command()
    async def reload(self, ctx, module: str) -> discord.Message:
        """Reloads cogs/modules from the bot."""
        if 'modules.' not in module:
            ext = "modules." + module
        try:
            ctx.bot.unload_extension(ext)
            ctx.bot.load_extension(ext)
            await ctx.send("The module has successfully been reloaded.")
        except ModuleNotFoundError:
            return await ctx.send("Couldn't find that module.")
        except Exception as e:
            error = ("Exception in loading module '{}'\n"
              "".format(module))
            error += "".join(traceback.format_exception(type(e), e,
                            e.__traceback__))
            self._cog_error = error
            try:
                await ctx.author.send("```py\n"+error+"\n```")
            except discord.errors.Forbidden:
                return await ctx.send("Module was found and possibly loaded, but "
                                      "something went wrong. "
                                      "Check your console "
                                      "for more information.")

            return await ctx.send("Module was found and possibly loaded, but "
                                 "something went wrong. "
                                 "I've sent you more information in DMs.")
def setup(bot):
    bot.add_cog(Developer(bot))
