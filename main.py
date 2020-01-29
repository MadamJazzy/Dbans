import discord
import asyncio
from handlers.bot import Bot
from handlers.data import rethink as re

bot = Bot(command_prefix='~')

@bot.check
async def check(ctx) -> bool:
    return True

    dbans = discord.utils.get(ctx.bot.guilds, id=269262004852621312)
    role = discord.utils.get(dbans.roles, id=444604902543458305)
    trusted = discord.utils.get(dbans.roles, id=478237848454168577)

    if ctx.author.bot:
        return False

    if role in ctx.author.roles:
        return True

    if trusted in ctx.author.roles:
        return True

    if ctx.author.id not in bot.allowed_users:
        bot.logger.info(f"{ctx.author} ({ctx.author.id}):"
                            " tried to execute a command without"
                            " proper permissions. Failing sliently...")
        return False

    return True

async def get_token() -> str:
    token = "NjcwNzY1NDU4OTExMjY0Nzc4.XizJCg.zU6myoowbWCOZHhPUm1Oy2a27p4"
    return token

loop = asyncio.get_event_loop()
try:
    token = loop.run_until_complete(get_token())
    loop.run_until_complete(bot.start(token))
except KeyboardInterrupt:
    loop.run_until_complete(bot.logout())
finally:
    loop.close
