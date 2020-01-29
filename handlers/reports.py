from .data import rethink as r
import discord
from typing import Union

class Reports:
    """This should handle most things related to reports."""

    async def queue(self, user: discord.User,
                    reporter: Union[discord.Member, discord.User],
                    reason: str, proof: Union[list, str],
                    channel: discord.TextChannel) -> discord.Message:

        """Adds a case to be approved/denied."""
        embed = discord.Embed(color=discord.Color(0x3498db))
        report_ee = f"User Tag: {user}\n"
        report_ee = report_ee + f"User ID: {user.id}\n"
        report_ee = report_ee + f"Avatar: [Click Here]({user.avatar_url})"
        embed.set_author(name=str(reporter) + " has submitted a report",
                         icon_url=reporter.avatar_url)
        embed.set_thumbnail(url=user.avatar_url)
        embed.add_field(name="**Reported User**", value=report_ee)
        embed.add_field(name="**Reason**", value=reason)
        # embed.add_field(name="**Proof:**", value="** **", inline=False)
        if isinstance(proof, str):
            embed.set_image(url=proof)
        elif isinstance(proof, list) and len(proof) == 1:
            embed.set_image(url=proof[0])
        message = (await channel.send(embed=embed))
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        if not isinstance(proof, str) and len(proof) > 1:
            for proof in proof:
                await channel.send(proof)
        return message

    async def add_user(self, user_id: Union[int, str],
                      reason: str, proof: Union[list, str],
                      reporter: Union[int, str]) -> dict:
        """Adds a user to the ban list."""
        user_id = str(user_id)
        reporter = str(reporter)
        ban_list = (await r.find('users', 'bans'))
        case_id = str(len(ban_list) + 1)
        if isinstance(proof, str):
            proof = [proof]

        report = {case_id: {}}
        report[case_id]['proof'] = proof
        report[case_id]['reason'] = reason
        report[case_id]['user_id'] = user_id
        report[case_id]['banned'] = True
        report[case_id]['appealed'] = False
        report[case_id]['reporter'] = reporter
        report[case_id]['case_id'] = case_id

        print((await r.update('users', 'bans', report)))
        return report

    async def appeal_user(self, user_id: int) -> Union[dict, None]:
        """Appeals a user.
           Returns None if the user is not banned."""
        user_id = str(user_id)
        ban_list = (await r.find('users', 'bans'))
        for case_id in ban_list:
            if ban_list[case_id]['user_id'] == user_id:
                case = {case_id: {}}
                case[case_id]['banned'] = False
                case[case_id]['appealed'] = True

                await r.update('users', 'bans', case)
                return case
            else:
                continue

        return None


    async def fetch(self, entity: Union[str, int]) -> Union[dict, None]:
        """Fetches a user or a case from the ban list. Case IDs are strings.
           Returns None if the case cannot be found, or if the user is not banned."""
        if isinstance(entity, int):
            user_id = str(entity)

            ban_list = (await r.find('users', 'bans'))
            for case_id in ban_list:
                if user_id == ban_list[case_id]['user_id']:
                    return ban_list[case_id]
                else:
                    continue

            return None

        else:
            case_id = entity
            ban_list = (await r.find('users', 'bans'))
            return ban_list.get(case_id)

reports = Reports()
