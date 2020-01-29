import discord.utils
import discord.utils
from discord.ext import commands


def is_dev_check(ctx):
    dev1 = discord.utils.get(ctx.guild.roles, id=392749579248074754)
    if dev1 in ctx.message.author.roles:
        return True
    else:
        return False


def is_dev():
    return commands.check(is_dev_check)


def is_staff_check(ctx):
    v = discord.utils.get(ctx.guild.roles, id=670790943246516236)
    if v in ctx.message.author.roles:
        return True
    else:
        return False


def is_staff():
    return commands.check(is_staff_check)


def is_trusted_check(ctx):
    t = discord.utils.get(ctx.guild.roles, id=670759575695261708)
    if t in ctx.message.author.roles:
        return True
    else:
        return False


def is_trusted():
    return commands.check(is_trusted_check)


def embed_perms(message):
    try:
        check = message.author.permissions_in(message.channel).embed_links
    except:
        check = True
    return check


def attach_perms(message):
    return message.author.permissions_in(message.channel).attach_files


def add_reaction_perms(message):
    return message.author.permissions_in(message.channel).add_reactions

