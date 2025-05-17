import datetime
from discord.ext import commands
from discord import app_commands
from typing import Literal
import discord
import json

with open("MinecadiaManagement/Assets/config.json", "r") as file:
    data = json.load(file)

class Ban(commands.Cog):
  def __init__(self, client: commands.Bot):
    self.client = client
  
  @app_commands.command(name="ban", description="Bans a user from this discord")
  @app_commands.checks.has_any_role(*data["ADMIN_ROLES"])
  @app_commands.describe(user="The user to ban from the discord", can_appeal="How long until they can appeal their ban")
  async def ban(self, interaction: discord.Interaction, user: discord.Member, can_appeal: Literal['1 Week', '2 Weeks', '3 Weeks', '4 Weeks', '8 Weeks', '12 Weeks', '24 Weeks', '36 Weeks', '48 Weeks']):
    return await interaction.response.send_message(content = "Please manually ban or use the other `/ban` command!")
    if interaction.guild is None:
            return await interaction.response.send_message(content="Commands cannot be ran in DMs!", ephemeral=True)
    await interaction.response.send_message(content="Attempting to ban user...")
    role = interaction.guild.get_role(1184716835879403541)
    await user.add_roles(role)
    can_appeal = int(float(datetime.datetime.utcnow().timestamp())) + (int(can_appeal.split(' ')[0])*604800)
    async with await get_pool() as pool:
            async with pool.acquire() as mydb:
                async with mydb.cursor() as cursor:
                    await cursor.execute(f"INSERT INTO `bans` (`user_id`, `can_appeal`) VALUES ('{user.id}', '{can_appeal}')")
            pool.close()
            await pool.wait_closed()
    await interaction.edit_original_response(content=f"Successfully banned {user} for until <t:{can_appeal}:R>")

  @app_commands.command(name="delete", description="Deletes messages")
  async def delete(self, interaction: discord.Interaction):
    await interaction.response.send_message(content = "`✅` Starting to delete messages in Text Channels...")
    bot_channel = interaction.guild.get_channel(935016733033525328)
    bad_words = ["autistic", "b1tch", "beaner", "aeaner", "binghamton", "bitch", "chigga", "ching chong", "chink", "coon", "cracker", "cunt", "cunts", "curry muncher", "ddos", "ddoss", "discord.gg/mcwealth", "dominic", "dominic iannacci", "dos", "doss", "dox", "doxbin", "doxbin.org", "e-slut", "e-whore", "eslut", "ewhore", "f@g", "f@ggot", "faggot", "hit off", "https://youtu.be/qCgc31iYbck", "iannacci", "inbred", "jap", "jig", "jigaboo", "jigarooni", "jigg", "jiggabo", "jigger", "jijjiboo", "kitchener", "n!g", "n!gga", "n!gger", "n1g", "n1gga", "n1gger", "negro", "ngga", "n*gga", "nigga", "niggas", "nigger", "nigger", "niqqa", "niqqas", "p3do", "paki", "ped0", "pedo", "qcgc31iybck", "sand monkey", "sex", "slut", "spic", "sukenmc", "swat", "swatted", "tranny", "trans", "trany", "whitman", "whore", "zigabo", "fag", "fags", "kill yourself", "kys", "kill urself", "killing yourself", "retard", "retarded", "retards", "rape", "raped", "cock", "fag*ot", "raping", "rapes", "nig", "nig-ger", "Arse", "Ass","Asshole","Homosexual", "Homophobic","Racist","Gay","Lgbt","Jew","Jewish","Anti-semitic","Chink","Muslims","Muslim","Isis","Islamophobe","homophobe ","Bombing","Sexyhot","Bastard","Bitch","Fucker","Cunt","Damn","Fuck","Goddamn","Shit","Motherfucker","Nigga","Nigger","Prick","Shit","shit ass","Shitass","son of a bitch","Whore","Thot","Slut","Faggot","Dick","Pussy","Penis","Vagina","Negro","Coon","Bitched","Sexist","Freaking","Cock","Sucker","Lick","Licker","Rape","Molest","Anal","Buttrape","Coont","Cancer","Sex","Retard","Fuckface","Dumbass","5h1t","5hit","A_s_s","a2m","a55","adult","amateur","anal","anal impaler†††","anal leakage†††","anilingus","anus","ar5e","arrse","arse","arsehole","ass","ass fuck†††","asses","assfucker","ass-fucker","assfukka","asshole","asshole","assholes","assmucus†††","assmunch","asswhole","autoerotic","b!tch","b00bs","b17ch","b1tch","ballbag","ballsack","bangbros","bareback","bastard","beastial","beastiality","beef curtain†††","bellend","bestial","bestiality","bi+ch","biatch","bimbos","birdlock","bitch","bitch tit†††","bitcher","bitchers","bitches","bitchin","bitching","bloody","blow job","blow me†††","blow mud†††","blowjob","blowjobs","blue waffle†††","blumpkin†††","boiolas","bollock","bollok","boner","boob","boobs","booobs","boooobs","booooobs","booooooobs","breasts","buceta","bugger","bum","bunny fucker","bust a load†††","busty","butt","butt fuck†††","butthole","buttmuch","buttplug","c0ck","c0cksucker","carpet muncher","carpetmuncher","cawk","chink","choade†††","chota bags†††","cipa","cl1t","clit","clit licker†††","clitoris","clits","clitty litter†††","clusterfuck","cnut","cock","cock pocket†††","cock snot†††","cockface","cockhead","cockmunch","cockmuncher","cocks","cocksuck ","cocksucked ","cocksucker","cock-sucker","cocksucking","cocksucks ","cocksuka","cocksukka","cok","cokmuncher","coksucka","coon","cop some wood†††","cornhole†††","corp whore†††","cox","cum","cum chugger†††","cum dumpster†††","cum freak†††","cum guzzler†††","cumdump†††","cummer","cumming","cums","cumshot","cunilingus","cunillingus","cunnilingus","cunt","cunt hair†††","cuntbag†††","cuntlick ","cuntlicker ","cuntlicking ","cunts","cuntsicle†††","cunt-struck†††","cut rope†††","cyalis","cyberfuc","cyberfuck ","cyberfucked ","cyberfucker","cyberfuckers","cyberfucking ","d1ck","damn","dick","dick hole†††","dick shy†††","dickhead","dildo","dildos","dink","dinks","dirsa","dirty Sanchez†††","dlck","dog-fucker","doggie style","doggiestyle","doggin","dogging","donkeyribber","doosh","duche","dyke","eat a dick†††","eat hair pie†††","ejaculate","ejaculated","ejaculates ","ejaculating ","ejaculatings","ejaculation","ejakulate","erotic","f u c k","f u c k e r","f_u_c_k","f4nny","facial†††","fag","fagging","faggitt","faggot","faggs","fagot","fagots","fags","fanny","fannyflaps","fannyfucker","fanyy","fatass","fcuk","fcuker","fcuking","feck","fecker","felching","fellate","fellatio","fingerfuck ","fingerfucked ","fingerfucker ","fingerfuckers","fingerfucking ","fingerfucks ","fist fuck†††","fistfuck","fistfucked ","fistfucker ","fistfuckers ","fistfucking ","fistfuckings ","fistfucks ","flange","flog the log†††","fook","fooker","fuck hole†††","fuck puppet†††","fuck trophy†††","fuck yo mama†††","fuck†††","fucka","fuck-ass†††","fuck-bitch†††","fucked","fucker","fuckers","fuckhead","fuckheads","fuckin","fucking","fuckings","fuckingshitmotherfucker","fuckme ","fuckmeat†††","fucks","fucktoy†††","fuckwhit","fuckwit","fudge packer","fudgepacker","fuk","fuker","fukker","fukkin","fuks","fukwhit","fukwit","fux","fux0r","gangbang","gangbang†††","gang-bang†††","gangbanged ","gangbangs ","gassy ass†††","gaylord","gaysex","goatse","god","god damn","god-dam","goddamn","goddamned","god-damned","ham flap†††","hardcoresex ","hell","heshe","hoar","hoare","hoer","homo","homoerotic","hore","horniest","horny","hotsex","how to kill","how to murdep","jackoff","jack-off ","jap","jerk","jerk-off ","jism","jiz ","jizm ","jizz","kawk","kinky Jesus†††","knob","knob end","knobead","knobed","knobend","knobend","knobhead","knobjocky","knobjokey","kock","kondum","kondums","kum","kummer","kumming","kums","kunilingus","kwif†††","l3i+ch","l3itch","labia","LEN","lmao","lmfao","lmfao","lust","lusting","m0f0","m0fo","m45terbate","ma5terb8","ma5terbate","mafugly†††","masochist","masterb8","masterbat*","masterbat3","masterbate","master-bate","masterbation","masterbations","masturbate","mof0","mofo","mo-fo","mothafuck","mothafucka","mothafuckas","mothafuckaz","mothafucked ","mothafucker","mothafuckers","mothafuckin","mothafucking ","mothafuckings","mothafucks","mother fucker","mother fucker†††","motherfuck","motherfucked","motherfucker","motherfuckers","motherfuckin","motherfucking","motherfuckings","motherfuckka","motherfucks","muff","muff puff†††","mutha","muthafecker","muthafuckker","muther","mutherfucker","n1gga","n1gger","nazi","need the dick†††","nigg3r","nigg4h","nigga","niggah","niggas","niggaz","nigger","niggers ","nob","nob jokey","nobhead","nobjocky","nobjokey","numbnuts","nazis","nut butter†††","nutsack","omg","orgasim ","orgasims ","orgasm","orgasms ","p0rn","pawn","pecker","penis","penisfucker","phonesex","phuck","phuk","phuked","phuking","phukked","phukking","phuks","phuq","pigfucker","pimpis","piss","pissed","pisser","pissers","pisses ","pissflaps","pissin ","pissing","pissoff ","poop","porn","porno","pornography","pornos","prick","pricks ","pron","pube","pusse","pussi","pussies","pussy","pussy fart†††","pussy palace†††","pussys ","queaf†††","queer","rectum","retard","rimjaw","rimming","s hit","s.o.b.","s_h_i_t","sadism","sadist","sandbar†††","sausage queen†††","schlong","screwing","scroat","scrote","scrotum","semen","sex","sh!+","sh!t","sh1t","shag","shagger","shaggin","shagging","shemale","shi+","shit","shit fucker†††","shitdick","shite","shited","shitey","shitfuck","shitfull","shithead","shiting","shitings","shits","shitted","shitter","shitters ","shitting","shittings","shitty ","skank","slope†††","slut","slut bucket†††","sluts","smegma","smut","snatch","son-of-a-bitch","spac","spunk","t1tt1e5","t1tties","teets","teez","testical","testicle","tit","tit wank†††","titfuck","tits","titt","tittie5","tittiefucker","titties","tittyfuck","tittywank","titwank","tosser","turd","tw4t","twat","twathead","twatty","twunt","twunter","v14gra","v1gra","vagina","viagra","vulva","w00se","wang","wank","wanker","wanky","whoar","whore","willies","willy","wtf","xrated","xxx","sucker","dumbass","Kys","Kill","Die","Cliff","Bridge","Shooting","Shoot","Bomb","Terrorist","Terrorism","Bombed","Trump","Maga","Conservative","Make america great again","Far right","Necrophilia","Mongoloid","Furfag","Cp","Pedo","Pedophile","Pedophilia","Child predator","Predatory","Depression","Cut myself","I want to die","Fuck life","Redtube","Loli","Lolicon","Cub"]
    channels = [1032633836208672818, 918903892144717915, 918904091906834452, 1066045406028505178, 1186037933136949258, 1012348851920834560, 1186037987369296003, 1222028922795982923, 1222029036411162739]
    forums = [1186037435646361721, 1186038080772255785, 1186038040435622030, 1222029114761019513]
    for chn in channels:
        chn_msgs = 0
        total = 0
        channel = interaction.guild.get_channel(chn)
        msg = await bot_channel.send(f"`🔄` Checking {channel.mention}...")
        async for message in channel.history(limit = None, oldest_first = True):
            total += 1
            if total % 1000 == 0:
               await msg.edit(content = f"`🔄` Checking {channel.mention}... `{total}` messages... `{chn_msgs}` deleted...")
            if any(word in message.content for word in bad_words):
              for word in message.content.lower().split(" "):
                if word.lower() in bad_words:
                    try:
                      print(f"[{message.author.name}#{message.author.discriminator}] [{word}]\n{message.content}\n")
                      await message.delete()
                      chn_msgs += 1
                    except Exception as e:
                       print(f"EXCEPTION: {e}")
        await msg.edit(content = f"`✅` Done {channel.mention} deleted `{chn_msgs}` messages.")
    for foru in forums:
        chn_msgs = 0
        total = 0
        forum = interaction.guild.get_channel(foru)
        msg = await bot_channel.send(f"`🔄` Checking {channel.mention}... ")
        for thread in forum.threads: 
          await msg.edit(content = f"`🔄` Checking {channel.mention}... {thread.mention}")
          async for message in thread.history(limit = None, oldest_first = True):
              total += 1
              if total % 1000 == 0:
               await msg.edit(content = f"`🔄` Checking {channel.mention}... `{total}` messages... `{chn_msgs}` deleted...")
              if any(word in message.content for word in bad_words):
                for word in message.content.lower().split(" "):
                  if word.lower() in bad_words:
                      try:
                        print(f"[{message.author.name}#{message.author.discriminator}] [{word}] [{thread.name}]\n{message.content}\n")
                        await message.delete()
                        chn_msgs += 1
                      except Exception as e:
                        print(f"EXCEPTION: {e}")
          await msg.edit(content = f"`✅` Done {channel.mention} deleted `{chn_msgs}` messages.")

  @ban.error
  async def ban_error(self, interaction: discord.Interaction, error):
    await interaction.edit_original_response(content=error)
    
async def setup(client:commands.Bot) -> None:
  await client.add_cog(Ban(client))