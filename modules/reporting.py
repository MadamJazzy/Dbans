import asyncio
import os
import discord
from typing import Union, Optional
from discord.ext import commands
from handlers.reports import reports as re
from handlers.data import rethink as db
from handlers import checks
import aiohttp

class Reporting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.quits = ['quit', 'exit', 'stop', 'cancel']
        self.reasons = {"A": "Proof is invalid, insufficient, or not"
                             " representative of reason.",
                        "B": "Reason cited is not covered by our policy.",
                        "C": "Our Report Policy does not cover this, "
                             "please report this to Discord's Trust and Safety team: https://dis.gd/howtoreport",
                        "D": "This report is a duplicate of a previous report.",
                        "E": "User is not clearly identifiable in proof.",
                        "F": "Report contains broken proof."}
        self.legend = {"🇦": "A", "🇧": "B", "🇨": "C", "🇩": "D", "🇪": "E", "🇫": "F"}
        self.numbers = {'1': '1\u20e3',
                        '2': '2\u20e3',
                        '3': '3\u20e3',
                        '4': '4\u20e3',
                        '5': '5\u20e3',
                        '6': '6\u20e3',
                        '7': '7\u20e3',
                        '8': '8\u20e3',
                        '9': '9\u20e3',
                        '10': '\U0001f51f'}
        self.shorten = True
        self.reports_id = 670780386934259733 #reports
        self.vote_count = 1 #use in production


    async def tiny(self, long_url: str=None):
        url = f"http://tinyurl.com/api-create.php?url={long_url}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as p:
                p = await p.text()
        return p

    def list_flatten(self, packed_list: list):
        flat_list = []
        for sublist in packed_list:
            if not isinstance(sublist, list):
                flat_list.append(sublist)
                continue
            for item in sublist:
                flat_list.append(item)
        return flat_list

    def embed_builder(self, embed_type, user=None, report=None,
                      reporter=None, reject_reason=None):
        if embed_type == 'vote_accepted':
            embed = discord.Embed(color=discord.Color(0x00ff7e),
                                  description=f"{user.mention} has accepted this report.")
            return embed
        elif embed_type == 'vote_reject_reason':
            description = f"{user.mention}, please react with your reasoning for "
            description += "declining this report.\n\n"
            description += "🇦 Invalid proof.\n"
            description += "🇧 Reason cited is not covered by our Report Policy.\n"
            description += "🇨 Report to discord.\n"
            description += "🇩 Report is a duplicate.\n"
            description += "🇪 User is not clearly identifiable in Proof\n"
#            description += "🇫 Broken proof."
            embed = discord.Embed(color=discord.Color(0x039be5),
                                  description=description)
            return embed
        elif embed_type == 'vote_rejected':
            embed = discord.Embed(color=discord.Color(0xff0000),
                                  description=f"{user.mention}"
                                  " has rejected this report with reasoning: "
                                  f"{reject_reason}.")
            return embed
        elif embed_type == 'report_accepted':
            report_ee = f"User Tag: {user}\n"
            report_ee = report_ee + f"User ID: {user.id}\n"
            reason = report['reason']
            proof = report['proof']
            embed = discord.Embed(color=discord.Color(0x00ff7e))
            embed.set_author(name=f"{str(reporter)}'s report has been accepted!",
                             icon_url=reporter.avatar_url)
            embed.set_thumbnail(url=user.avatar_url)
            embed.add_field(name="**Reported User:**",
                            value=report_ee)
            embed.add_field(name="**Reason:**",
                            value=reason)
            if isinstance(proof, str):
                embed.add_field(name="**Proof:**",
                                value=f"{proof}",
                                inline=False)
                # embed.set_image(url=proof)
            elif len(proof) == 1:
                embed.add_field(name="**Proof:**",
                                value=f"{proof[0]}",
                                inline=False)
                # embed.set_image(url=proof[0])
            else:
                proof_msg = ""
                for proof in proof:
                    proof_msg = proof_msg + f"{proof}\n"
                embed.add_field(name="**Proof:**",
                                value=proof_msg)
                embed.set_footer(text="Case ID: " + str(report['case_id']))
                return embed
        elif embed_type == 'report_rejected':
            report_ee = f"User Tag: {user}\n"
            report_ee = report_ee + f"User ID: {user.id}\n"
            reason = report['reason']
            proof = report['proof']
            embed = discord.Embed(color=discord.Color(0xfd2426),
                                  description="The report was rejected."
                                              f"\nReason: {reject_reason}")
            embed.set_author(name=f"{str(reporter)}'s report was rejected.",
                             icon_url=reporter.avatar_url)
            embed.set_thumbnail(url=user.avatar_url)
            embed.add_field(name="**Reported User:**",
                            value=report_ee)
            embed.add_field(name="**Reason:**",
                            value=reason)
            if isinstance(proof, str):
                embed.add_field(name="**Proof:**",
                                value=f"{proof}",
                                inline=False)
                # embed.set_image(url=proof)
            elif len(proof) == 1:
                embed.add_field(name="**Proof:**",
                                value=f"{proof[0]}",
                                inline=False)
                # embed.set_image(url=proof[0])
            else:
                proof_msg = ""
                for proof in proof:
                    proof_msg = f"{proof}\n"
                embed.add_field(name="**Proof:**",
                                value=proof_msg)
            return embed

    def reject_reason(self, report):
        reasons = report['reasons']
        reasons = sorted(reasons, key=reasons.get, reverse=True)
        return reasons[0]

    async def case_id(self):
        bans = (await db.find('users', 'bans'))
        return len(bans)

    async def temp_channels(self):
        return (await db.find('users', 'temp'))['channels']

    async def create_temp_channel(self, ctx):
        guild = ctx.guild
        bans = (await db.find('users', 'bans'))
        temp = (await db.find('users', 'temp'))
        name = 'report-' + str((len(temp['channels']) + len(bans) + 1))
        verified = discord.utils.get(ctx.guild.roles, name="Verified")
        overwrites = {
                ctx.author: discord.PermissionOverwrite(read_messages=True,
                                                        send_messages=True,
                                                        embed_links=True,
                                                        attach_files=True),
                guild.default_role: discord.PermissionOverwrite(read_messages=False,
                                                                    send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True),
                verified: discord.PermissionOverwrite(read_messages=True,
                                                      embed_links=True,
                                                      attach_files=True)
            }
        channel = (await guild.create_text_channel(name, overwrites=overwrites,
                                                   category=discord.utils.get(
                                                   ctx.guild.channels,
                                                   name="Reports")))
        await channel.edit(nsfw=True)
        temp['channels'].append(str(channel.id))
        await db.update('users', 'temp', temp)
        return channel

    async def remove_temp_channel(self, channel):
        temp = (await db.find('users', 'temp'))
        try:
            temp['channels'].remove(str(channel.id))
        except IndexError:
            pass
        await db.update('users', 'temp', temp)
        try:
            await channel.delete()
        except:
            pass


    async def urls(self, msg: discord.Message, name, iter=None) -> list:
        channels = (self.bot.get_all_channels())
        channel = discord.utils.get(channels, id=504064900273012760)
        urls = []
        i = 0
        for embed in msg.embeds:
            i += 1
            if iter is not None:
                name = name + f"-{iter}-{i}.png"
            else:
                name = name + f"-{i}.png"
            file = (await self.bot.download(embed.url, name))
            message = (await channel.send(file=file))
            os.remove(name)
            for attachment in message.attachments:
                if attachment.url in urls:
                    continue
                urls.append(attachment.url)
        for attachment in msg.attachments:
            if iter is not None:
                name = name + f"-{iter}-{i}.png"
            else:
                name = name + f"-{i}.png"
            file = (await self.bot.download(attachment.url, name))
            message = (await channel.send(file=file))
            os.remove(name)
            for a in message.attachments:
                urls.append(a.url)
        if self.shorten is True:
            urls2 = []
            for i in urls:
                urls2.append(await self.tiny(i))
                return urls2
        else:
            return urls


    @commands.command()
    async def banned(self, ctx, user: Union [discord.User, int]) -> discord.Message:
        """Checks if a user is banned."""
        user = user if isinstance(user, discord.User) else (await ctx.bot.get_user_info(user))
        case = await re.fetch(user.id)
        if case is None:
            embed = discord.Embed(color=discord.Color(0x00ff7e), title="DBans Lookup")
            embed.set_author(name=user, icon_url=user.avatar_url)
            embed.set_thumbnail(url=user.avatar_url)
            embed.add_field(name="UserID", value=f"{user.id}", inline=False)
            embed.add_field(name="User Name", value=f"{user.name}", inline=False)
            embed.add_field(name="Avatar", value=f"[Click here]({user.avatar_url})", inline=False)
            embed.add_field(name="Blacklisted", value="False, this user is not globally banned.", inline=False)
            return await ctx.send(embed=embed)

        elif case['banned']:
            embed = discord.Embed(color=discord.Color(0xfd2426), title="DBans Lookup")
            embed.set_author(name=user, icon_url=user.avatar_url)
            embed.set_thumbnail(url=user.avatar_url)
            embed.add_field(name="User ID", value=f"{user.id}", inline=False)
            embed.add_field(name="Username", value=f"{str(user)}", inline=False)
            embed.add_field(name="Avatar", value=f"[Click here]({user.avatar_url})", inline=False)
            embed.add_field(name="Globally Banned", value="This user is globally banned.", inline=False)
            embed.add_field(name="Case ID", value=f"{case['case_id']}", inline=False)
            embed.add_field(name="Reason", value=f"{case['reason']}", inline=False)
            proof = "\n".join(case['proof'])
            embed.add_field(name="Proof", value=proof, inline=False)
            return await ctx.send(embed=embed)
        elif case['appealed']:
            embed = discord.Embed(color=discord.Color(0x00ff7e), title="DBans Lookup")
            embed.set_author(name=user, icon_url=user.avatar_url)
            embed.set_thumbnail(url=user.avatar_url)
            embed.add_field(name="User ID", value=f"{user.id}", inline=False)
            embed.add_field(name="Username", value=f"{str(user)}", inline=False)
            embed.add_field(name="Avatar", value=f"[Click here]({user.avatar_url})", inline=False)
            embed.add_field(name="Globally Banned", value="This user is not globally banned. They appealed.", inline=False)
            embed.add_field(name="Case ID", value=f"{case['case_id']}", inline=False)
            embed.add_field(name="Reason", value=f"{case['reason']}", inline=False)
            proof = "\n".join(case['proof'])
            embed.add_field(name="Proof", value=proof, inline=False)
            await ctx.send(f"User is not banned. They appealed.\nCaseID: {case['case_id']}")
            return await ctx.send(embed=embed)


    @checks.is_dev()
    @commands.command(aliases=["rreason", "rr", "rejectr"])
    async def rejectreason(self, ctx, report_msg_id: int, *, reason: str) -> discord.Message:
        """Change reject reason of the report."""
        r = discord.utils.get(ctx.guild.roles, name="Verified")
        if not r in ctx.author.roles:
            return await ctx.send("You're not a Verified member.")
        channel = discord.utils.get(ctx.guild.channels, id=self.reports_id)
        try:
            m = await channel.get_message(report_msg_id)
            embed = m.embeds[0]
            embed.description = "The report was rejected.\nReason: " + reason
            await m.edit(embed=embed)
            return await ctx.send("Successfully edited reject reason.")
        except:
            return await ctx.send("I couldn't find that message.")

    @checks.is_staff()
    @commands.command(aliases=["qr", "qreason"])
    async def queuereason(self, ctx, case_id: Optional[int]=None, *, reason: str) -> discord.Message:
        """Changes reason of current or specified report."""
        r = discord.utils.get(ctx.guild.roles, name="Verified")
        if not r in ctx.author.roles:
            return await ctx.send("You're not a Verified member.")

        if not case_id is None:
            case = await re.fetch(case_id)
            channel = discord.utils.get(ctx.guild.channels, id=self.reports_id)
            found = False
            async for m in channel.history(limit=None):
                if m.embeds:
                    if m.embeds[0].color == discord.Color(0x00ff7e):
                        if f"Case ID: {str(case_id)}" == str(m.embeds[0].footer.text):
                            embed = m.embeds[0]
                            f = embed.fields[1]
                            embed.set_field_at(1, name=f.name, value=reason, inline=f.inline)
                            bans = (await db.find('users', 'bans'))
                            bans[str(case_id)]["reason"] = reason
                            await db.update('users', 'bans', bans)
                            await m.edit(embed=embed)
                            found = True
                            return await ctx.send("Successfully edited report reason.")
            if found is False:
                return await ctx.send("I couldn't find that case.")
        else:
            if not ctx.channel.name.startswith("report-"):
                return await ctx.send("This is not a report channel.")
            async for m in ctx.channel.history(limit=None):
                if m.embeds:
                    if m.embeds[0].color == discord.Color(0x3498db):
                        embed = m.embeds[0]
                        f = embed.fields[1]
                        embed.set_field_at(1, name=f.name, value=reason, inline=f.inline)
                        reports = (await db.find('users', 'reports'))
                        reports[str(m.id)]["reason"] = reason
                        await db.update('users', 'reports', reports)
                        await m.edit(embed=embed)
                        return await ctx.send("Successfully edited current report reason.")

    @checks.is_staff()
    @commands.command(aliases=["ap"])
    async def addproof(self, ctx, case_id: Optional[int]=None, proof: str=None) -> discord.Message:
        """Adds proof to current or specified report."""
        r = discord.utils.get(ctx.guild.roles, name="Verified")
        if not r in ctx.author.roles:
            return await ctx.send("You're not a Verified member.")

        channels = (self.bot.get_all_channels())
        channel = discord.utils.get(channels, id=504064900273012760)

        if proof is None:
            if ctx.message.attachments is None:
                return await ctx.send("Proof needs to be link or attached image.")
            proof = ctx.message.attachments[0].url

        name = "report-proof" + "." + proof.split(".")[-1]
        file = (await self.bot.download(proof, name))
        message = (await channel.send(file=file))
        os.remove(name)
        proof = message.attachments[0].url

        if not case_id is None:
            case = await re.fetch(case_id)
            channel = discord.utils.get(ctx.guild.channels, id=self.reports_id)

            found = False
            async for m in channel.history(limit=None):
                if m.embeds:
                    if m.embeds[0].color == discord.Color(0x00ff7e):
                        if f"Case ID: {str(case_id)}" == str(m.embeds[0].footer.text):
                            embed = m.embeds[0]
                            f = embed.fields[2]
                            bans = (await db.find('users', 'bans'))
                            if self.shorten is True:
                                proof = (await self.tiny(proof))
                            bans[str(case_id)]["proof"].append(proof)
                            await db.update('users', 'bans', bans)
                            p = "\n".join(bans[str(case_id)]["proof"])
                            embed.set_field_at(2, name=f.name, value=p, inline=f.inline)
                            await m.edit(embed=embed)
                            found = True
                            return await ctx.send("Successfully edited report proof.")
            if found is False:
                return await ctx.send("I couldn't find that case.")
        else:
            if not ctx.channel.name.startswith("report-"):
                return await ctx.send("This is not a report channel.")
            async for m in ctx.channel.history(limit=None):
                if m.embeds:
                    if m.embeds[0].color == discord.Color(0x3498db):
                        reports = (await db.find('users', 'reports'))
                        if self.shorten is True:
                            proof = (await self.tiny(proof))
                        reports[str(m.id)]["proof"].append(proof)
                        await db.update('users', 'reports', reports)
                        return await ctx.send("Successfully edited current report proof.")

    @checks.is_staff()
    @commands.command(aliases=["rp"])
    async def removeproof(self, ctx, case_id: Optional[int]=None) -> discord.Message:
        """Removes proof from current or specified report."""
        r = discord.utils.get(ctx.guild.roles, name="Verified")
        n = 1
        value = ""
        if not r in ctx.author.roles:
            return await ctx.send("You're not a Verified member.")

        if not case_id is None:
            case = await re.fetch(case_id)
            channel = discord.utils.get(ctx.guild.channels, id=self.reports_id)
            found = False
            async for m in channel.history(limit=None):
                if m.embeds:
                    if m.embeds[0].color == discord.Color(0x00ff7e):
                        if f"Case ID: {str(case_id)}" == str(m.embeds[0].footer.text):
                            embed = m.embeds[0]
                            f = embed.fields[2]
                            bans = (await db.find('users', 'bans'))
                            for i in bans[str(case_id)]["proof"]:
                                value += f"\n{n}. " + i
                                n += 1
                            e = discord.Embed(color=discord.Color(0x00ff7e))
                            e.add_field(name="Choose the proof to be removed.", value=value)
                            mm = await ctx.send(ctx.author.mention, embed=e)
                            if n < 12:
                                for i in range(1, n):
                                    await mm.add_reaction(self.numbers[str(i)])
                                await mm.add_reaction("🇽")
                                def check(reaction, user):
                                    return reaction.message.channel == ctx.channel and user == ctx.author
                                reaction, user = (await ctx.bot.wait_for('reaction_add', check=check))
                                for key, value in self.numbers.items():
                                    if value == reaction.emoji:
                                        msg = int(key)
                                if reaction.emoji == "🇽":
                                    return await ctx.send("Exiting...")
                            else:
                                def check(msg):
                                    return msg.channel == ctx.channel and msg.author == ctx.author
                                msg = (await ctx.bot.wait_for('message', check=check)).content
                                if msg in self.quits:
                                    return await ctx.send("Exiting...")
                            bans[str(case_id)]["proof"].pop(int(msg)-1)
                            await db.update('users', 'bans', bans)
                            p = "\n".join(bans[str(case_id)]["proof"])
                            embed.set_field_at(2, name=f.name, value=p, inline=f.inline)
                            await m.edit(embed=embed)
                            found = True
                            return await ctx.send("Successfully edited report proof.")
            if found is False:
                return await ctx.send("I couldn't find that case.")

        else:
            if not ctx.channel.name.startswith("report-"):
                return await ctx.send("This is not a report channel.")
            async for m in ctx.channel.history(limit=None):
                if m.embeds:
                    if m.embeds[0].color == discord.Color(0x3498db):
                        reports = (await db.find('users', 'reports'))
                        for i in reports[str(m.id)]["proof"]:
                            value += f"\n{n}. " + i
                            n += 1
                        e = discord.Embed(color=discord.Color(0x00ff7e))
                        e.add_field(name="Choose the proof to be removed.", value=value)
                        mm = await ctx.send(ctx.author.mention, embed=e)
                        if n < 12:
                            for i in range(1, n):
                                await mm.add_reaction(self.numbers[str(i)])
                            await mm.add_reaction("🇽")
                            def check(reaction, user):
                                return reaction.message.channel == ctx.channel and user == ctx.author
                            reaction, user = (await ctx.bot.wait_for('reaction_add', check=check))
                            for key, value in self.numbers.items():
                                if value == reaction.emoji:
                                    msg = int(key)
                            if reaction.emoji == "🇽":
                                return await ctx.send("Exiting...")
                        else:
                            def check(msg):
                                return msg.channel == ctx.channel and msg.author == ctx.author
                            msg = (await ctx.bot.wait_for('message', check=check)).content
                            if msg in self.quits:
                                return await ctx.send("Exiting...")
                        reports[str(m.id)]["proof"].pop(int(msg)-1)
                        await db.update('users', 'reports', reports)
                        return await ctx.send("Successfully edited current report proof.")

    @checks.is_staff()
    @commands.command()
    async def votestats(self, ctx,
                        user: discord.Member=None) -> discord.Message:
        """Shows the most active verifieds!"""
        votestats = (await db.find('users', 'votestats'))
        embed = discord.Embed(color=discord.Color(0x7289da))
        if user is None:
            votes = sorted(votestats, key=votestats.get, reverse=True)
            message = "**__Vote Statistics__**\n\n"
            embed.add_field(name=message, value="\u200B")
            for vote in votes:
                user = discord.utils.get(ctx.guild.members, id=int(vote))
                if user is None:
                    continue
                embed.add_field(name=f"{user}",
                                 value=f"Votes: {votestats[vote]}", inline=True)
            await ctx.send(embed=embed)
        else:
            verified = discord.utils.get(ctx.guild.roles, name="Verified")
            if user == ctx.author:
                if votestats.get(str(user.id)) is None:
                    return await ctx.send("You haven't voted.")
                else:
                    stats = votestats.get(str(user.id))
                    if stats == 1:
                        message = "Your Vote Stats"
                        description = "You've voted once."
                        embed = discord.Embed(color=discord.Color(0x7289da), title=message, description=description)
                        await ctx.send(embed=embed)
                    else:
                        message = "Your Vote Stats"
                        description = f"{stats} votes."
                        embed = discord.Embed(color=discord.Color(0x7289da), title=message, description=description)
                        await ctx.send(embed=embed)
            else:
                if not verified in user.roles:
                    return await ctx.send("That user isn't a member of the staff team!")
                if votestats.get(str(user.id)) is None:
                    return await ctx.send("That user hasn't voted.")
                else:
                    stats = votestats.get(str(user.id))
                    if stats == 1:
                        message = f"{user}'s Vote Stats"
                        description = f"1 vote."
                        embed = discord.Embed(color=discord.Color(0x7289da), title=message, description=description)
                        await ctx.send(embed=embed)
                    else:
                        message = f"{user}'s Vote Stats"
                        description = f"{stats} votes."
                        embed = discord.Embed(color=discord.Color(0x7289da), title=message, description=description)
                        await ctx.send(embed=embed)

    @commands.command()
    async def report(self, ctx) -> discord.Message:
        """Reports a user."""
        await ctx.message.delete()
        guild = ctx.guild
        channel = await self.create_temp_channel(ctx)
        await channel.send(f"{ctx.author.mention}, "
                           "please send the ID of "
                           "the user you are reporting."
                           " Use `quit`, `exit`, `stop` or `cancel` at any time to"
                           " exit.")
        info = (await ctx.send(f"Please move to {channel.mention}."))
        def check(m):
            return m.channel == channel and m.author == ctx.author
        message1 = (await ctx.bot.wait_for('message', check=check)).content
        await info.delete()
        if message1.lower() in self.quits:
            await channel.send("Exiting...")
            await asyncio.sleep(1)
            await self.remove_temp_channel(channel)
        try:
            report_userid = int(message1)
            is_int = True
        except ValueError:
            is_int = False
        while is_int is False:
            await channel.send("Please send a user ID!")
            message1 = (await ctx.bot.wait_for('message', check=check)).content
            if message1.lower() in self.quits:
                await channel.send("Exiting...")
                await asyncio.sleep(1)
                await self.remove_temp_channel(channel)
            try:
                report_userid = int(message1)
                is_int = True
                break
            except ValueError:
                is_int = False
        try:
            user = (await ctx.bot.get_user_info(report_userid))
            is_user = True
        except discord.errors.NotFound:
            is_user = False
        while is_user is False:
            if is_int is True:
                await channel.send("I couldn't find that user."
                                  " Please send a valid user ID."
                                  " You can get one by using developer mode.")
            message1 = (await ctx.bot.wait_for('message', check=check)).content
            if message1 in self.quits:
                await channel.send("Exiting...")
                await asyncio.sleep(1)
                await self.remove_temp_channel(channel)
            try:
                user = (await ctx.bot.get_user_info(int(message1)))
                is_user = True
                break
            except ValueError:
                await channel.send("Please send a user ID!")
                is_user = False
                is_int = False
            except discord.errors.NotFound:
                is_user = False
                is_int = True

        await channel.send("Please send the reason for the report.")
        reason = (await ctx.bot.wait_for('message', check=check)).content
        if reason in self.quits:
            await channel.send("Exiting...")
            await asyncio.sleep(1)
            await self.remove_temp_channel(channel)
        await channel.send("Please send the proof for the report.")
        message3 = (await ctx.bot.wait_for('message', check=check))
        all_proofs = []
        async def proofing(message3, iter=None):
            if message3.content in self.quits:
                await channel.send("Exiting...")
                await asyncio.sleep(1)
                await self.remove_temp_channel(channel)
            await asyncio.sleep(1) # Embeds take some time to load, and sometimes don't register.
            proof = (await self.urls(message3, channel.name, iter=iter))
            if proof is None:
                proof = []
            while len(proof) == 0:
                await channel.send("Please send proof either as a link or"
                                    " by uploading the image one at a time.")
                message3 = (await ctx.bot.wait_for('message', check=check))
                if message3.content in self.quits:
                    await channel.send("Exiting...")
                    await asyncio.sleep(1)
                    await self.remove_temp_channel(channel)
                await asyncio.sleep(1) # Embeds take time to load.
                proof = (await self.urls(message3, channel.name, iter=iter))
            return proof
        my_lack_of_variable_names = (await proofing(message3, iter=0))
        all_proofs.append(my_lack_of_variable_names)
        await channel.send("Send any more proof you have 1 at a time. "
                           "Type `done` when you're finished.")

        proofs_ = await ctx.bot.wait_for('message', check=check)
        i = 0
        while not proofs_.content.lower() in ["done", 'finished']:
            if proofs_.content.lower() in self.quits:
                await channel.send("Exiting...")
                await asyncio.sleep(1)
                await self.remove_temp_channel(channel)
            i += 1
            all_proofs.append((await proofing(proofs_, iter=i)))
            await channel.send("If you have more proof, send it."
                               " Otherwise type `done` when you're finished.")
            proofs_ = await ctx.bot.wait_for('message', check=check)
        await channel.send("Your report has been queued. "
                              "You will receive a message when we"
                              " reach a verdict. I will delete the channel in"
                              " 2 seconds...")
        await asyncio.sleep(2)
        name = channel.name
        temp = await db.find('users', 'temp')
        temp['channels'].remove(str(channel.id))
        await channel.delete()
        verified = discord.utils.get(ctx.guild.roles, name="Verified")
        overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False,
                                                                    send_messages=True),
                ctx.guild.me: discord.PermissionOverwrite(read_messages=True),
                verified: discord.PermissionOverwrite(read_messages=True,
                                                      embed_links=True,
                                                      attach_files=True)
            }
        channel = (await guild.create_text_channel(name, overwrites=overwrites,
                                                   category=discord.utils.get(
                                                   ctx.guild.channels,
                                                   name="Reports")))

        await channel.edit(nsfw=True)
        temp = await db.find('users', 'temp')
        temp['channels'].append(str(channel.id))
        await db.update('users', 'temp', temp)
        all_proofs = self.list_flatten(all_proofs)
        report = (await re.queue(user, ctx.author, reason, all_proofs, channel))
        reports = (await db.find('users', 'reports'))
        votes = (await db.find('users', 'votes'))
        reports[str(report.id)] = {'user_id': str(user.id),
                                        'reason': reason, 'proof': all_proofs,
                                        'reporter': str(ctx.author.id)}
        votes[str(report.id)] = {
                                      'votes': 0, 'rejects': 0, 'reasons':
                                      {
                                       "A": 0, "B": 0, "C": 0, "D": 0, "E": 0
                                       }, 'authors': {}
                                     }

        await db.update('users', 'reports', reports)
        await db.update('users', 'votes', votes)
        ctx.bot.dispatch('report', ctx.author, user)

    async def on_report_accepted(self, report):
        dbans = discord.utils.get(self.bot.guilds, id=269262004852621312)
        c = discord.utils.get(dbans.channels, id=506562917924077589)
        user = (await self.bot.get_user_info(int(report['user_id'])))
        reporter = (await self.bot.get_user_info(int(report['reporter'])))
        try:
            await reporter.send("Your report has been accepted!")
        except:
            pass
        report = (await re.add_user(report['user_id'], report['reason'],
                                    report['proof'], reporter.id))
        case_id = str(await self.case_id())
        embed = self.embed_builder('report_accepted', reporter=reporter,
                                   user=user, report=report[case_id])
        await c.send(embed=embed)

    async def on_report_rejected(self, report, reason):
        dbans = discord.utils.get(self.bot.guilds, id=269262004852621312)
        c = discord.utils.get(dbans.channels, id=506562917924077589)
        user = (await self.bot.get_user_info(int(report['user_id'])))
        reporter = (await self.bot.get_user_info(int(report['reporter'])))
        try:
            await reporter.send(f"Your report has been declined. Reason: `{reason}`")
        except:
            pass
        embed = self.embed_builder('report_rejected', reporter=reporter,
                                   user=user, reject_reason=reason,
                                   report=report)
        await c.send(embed=embed)

    async def on_vote_update(self, message, user, vote, has_accepted=None,
                             has_rejected=None):
        dbans = discord.utils.get(self.bot.guilds, id=269262004852621312)
        c = discord.utils.get(dbans.channels, id=506562917924077589)
        reports = (await db.find('users', 'reports'))[str(message.id)]
        votes = (await db.find('users', 'votes'))
        if vote == 'accept':
            embed = self.embed_builder('vote_accepted', user)
            votes[str(message.id)]['votes'] += 1
            await db.update('users', 'votes', votes)
            await message.channel.send(embed=embed)
            if votes[str(message.id)]['votes'] >= 5:
                self.bot.dispatch('report_accepted', reports)
                await message.channel.send("Report has been accepted. "
                                           "Deleting channel in 5 seconds...")
                await asyncio.sleep(5)
                await self.remove_temp_channel(message.channel)
            elif votes[str(message.id)]['rejects'] >= 5:
                self.bot.dispatch('report_rejected', reports)
                await message.channel.send("Report has been rejected. "
                                           "Deleting channel in 5 seconds...")
                await asyncio.sleep(5)
                await self.remove_temp_channel(message.channel)

        else:
            embed = self.embed_builder('vote_reject_reason', user)
            a = (await message.channel.send(embed=embed))
            def check(r, m):
                return r.message.channel == message.channel and \
                    m == user and r.emoji in self.legend # and r.message == a
            await a.add_reaction("🇦")
            await a.add_reaction("🇧")
            await a.add_reaction("🇨")
            await a.add_reaction("🇩")
            await a.add_reaction("🇪")
            #await a.add_reaction("🇫")
            r, m = await self.bot.wait_for('reaction_add', check=check)
            e = self.legend[r.emoji]
            votes[str(message.id)]['rejects'] += 1
            votes[str(message.id)]['authors'][str(user.id)] = e
            votes[str(message.id)]['reasons'][e] += 1
            await db.update('users', 'votes', votes)
            e = self.reasons[e]
            embed = self.embed_builder('vote_rejected', user,
                                       reject_reason=e)
            await message.channel.send(embed=embed)
            await a.delete()
            if votes[str(message.id)]['votes'] >= 5:
                self.bot.dispatch('report_accepted', reports)
                await message.channel.send("Report has been accepted. "
                                           "Deleting channel in 5 seconds...")
                await asyncio.sleep(5)
                await self.remove_temp_channel(message.channel)
            elif votes[str(message.id)]['rejects'] >= 5:
                reason = self.reject_reason(votes[str(message.id)])
                reason = self.reasons[reason]
                self.bot.dispatch('report_rejected', reports,
                                  reason)
                await message.channel.send("Report has been rejected. "
                                           "Deleting channel in 5 seconds...")
                await asyncio.sleep(5)
                await self.remove_temp_channel(message.channel)

    async def on_guild_channel_delete(self, channel):
        if str(channel.id) in (await self.temp_channels()):
            await self.remove_temp_channel(channel)


def setup(bot):
    bot.add_cog(Reporting(bot))
