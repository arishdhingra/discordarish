import nextcord
from nextcord.ext import commands, tasks
import config
import random
import pymongo
import asyncio


pyClient = pymongo.MongoClient(config.mongoDB)
database = pyClient["discord"]

intents = nextcord.Intents.all()

client = commands.Bot(intents=intents)


# on ready
@client.event
async def on_ready():
    print("Bot is ready")
    remove_user.start()


# Generating a Random Key for user to claim and get access to the channel
@commands.has_permissions(administrator=True)
@client.slash_command(name="generate", description="Generates Key For Users")
# only Admins can use this command
async def generate(
    interaction: nextcord.Interaction,
    days: int,
    roles: str = nextcord.SlashOption(
        name="role",
        choices={
            "Platinum Top Tier": "1046690687904649287",
            "Gold Crypto Picks": "1046690132423610408",
            "Gold Sports Picks": "1046690679948066856",
        },
    ),
):

    # Getting the role from the choices

    role = interaction.guild.get_role(int(roles))

    # Generating 32 character key for user to claim (A,a,0)
    key = random.choices(  # Generating Random Characters
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789", k=32
    )
    key = "".join(key)  # Joining the characters to form a string

    # Now Saving the key to the keys.txt file
    with open("keys.txt", "a") as f:
        f.write(f"{key} {days} {role.id}\n")

    print(f"{interaction.user} generated a key for {days} days with role {role.name}")

    await interaction.response.send_message(f"Key Generated: {key}", ephemeral=True)


# Claiming the key and getting access to the channel
@client.slash_command(name="claim", description="Claim Key")
async def claim(interaction: nextcord.Interaction, key: str):

    await interaction.response.defer()

    # Reading the keys.txt file
    with open("keys.txt", "r") as f:
        keys = f.readlines()

    # Checking if the key is valid or not
    await asyncio.sleep(1)
    await interaction.followup.send("Please Wait Checking Key.....", delete_after=10)
    for line in keys:
        if key in line:
            key, days, role_id = line.split()

            # Getting the role object
            role = interaction.guild.get_role(int(role_id))
            print(role)

            try:
                # Adding user to the role
                await interaction.user.add_roles(role)
            except:
                print(
                    "Roles Pemission Issue. Please Bring the Bot Role Above the Role You Want to Give"
                )
                await interaction.followup.send(
                    f"CANNOT GIVE ROLE: Bot Role is below {role.name} Role. Please Bring the Bot Role Above the Role You Want to Give",
                    delete_after=10,
                )
                return
            # Sending the user a message
            await interaction.followup.send(
                f"Successfully Claimed Key for {days} days",
                delete_after=10,
            )
            print(f"{interaction.user} claimed key for {days} days")

            # Removing the key from the keys.txt file
            keys.remove(line)

            # Saving the keys.txt file
            with open("keys.txt", "w") as f:
                f.writelines(keys)

            # Saving the user to the database

            if database["users"].find_one({"user_id": interaction.user.id}) is None:
                database["users"].insert_one(
                    {
                        "user_id": interaction.user.id,
                        "days": int(days),
                        "role_id": int(role_id),
                        "guild_id": interaction.guild.id,
                    }
                )
            else:
                # Adding the days to the user
                database["users"].update_one(
                    {"user_id": interaction.user.id},
                    {"$inc": {"days": int(days)}},
                )

            return

    await interaction.followup.send("Invalid Key.....", delete_after=10)
    return


# Removing the user from the channel after the days are over
@tasks.loop(hours=24)
async def remove_user():
    print("Ckecking Users")
    users = database["users"].find()

    for user in users:
        # Remainder for the User
        if user["days"] == 1:
            try:
                # Sending the Remainder for the user
                member = client.get_user(user["user_id"])
                await member.send(
                    f"Your subscription is set to expire in 24 hours. Please contact <@{config.userID}> to extend the membership."
                )
                print(f"Remainder Sent to {member}")
            except:
                print(f"Couldn't send message to {member}")
                pass

        if user["days"] <= 0:
            role = client.get_guild(user["guild_id"]).get_role(user["role_id"])
            guild = client.get_guild(user["guild_id"])
            member = guild.get_member(user["user_id"])
            await member.remove_roles(role)

            print(f"Removed {member} from  {role}")
            database["users"].delete_one({"user_id": user["user_id"]})
            await member.send(
                f"Your membership is now ended, Please contact <@{config.userID}> to re-enroll"
            )
        else:
            database["users"].update_one(
                {"user_id": user["user_id"]}, {"$inc": {"days": -1}}
            )


client.run(config.token)
# https://discord.com/api/oauth2/authorize?client_id=1047215765155233892&permissions=8&scope=bot%20applications.commands
