import os
from kanji import Kanji
from dotenv import load_dotenv
from discord import Message, Intents, Interaction, app_commands, File
from discord.ext import commands
from discord.utils import escape_markdown

bot = commands.Bot(command_prefix="!", intents=Intents.all())

load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")


@bot.event
async def on_ready():
    print(f'Logged on as {bot.user}!')

    await bot.tree.sync()


@bot.listen()
async def on_message(message: Message):
    if not message.author.bot:
        print(f'Message from {message.author}: {message.content}')

        try:
            kanji = Kanji(message.content)
        except TypeError:
            await message.reply("Вы ввели больше одного символа")
            raise
        except ValueError:
            await message.reply("Это не кандзи. Пожалуйста, введите кандзи")
            raise

        kanji_data = kanji.get_info()

        rusnick = (escape_markdown(kanji_data['RusNick']) or
               "значение для этого кандзи отсутствует в базе данных или ещё не добавлено")
        
        grade = escape_markdown(kanji_data.get("grade", ""))
        readings_meanings = '\n'.join(kanji_data['readings_meanings'])

        extra_1, extra_2 = "", ""
        if extra_meanings := kanji_data.get('extras', ""):
            if extra_meanings['^']:
                extra_1 = "(" + ";".join(extra_meanings['^']) + ")"
            if extra_meanings["*"]:
                extra_2 = "[" + ";".join(extra_meanings['*']) + "]"
    
        await message.channel.send(f"{grade}\n*{kanji_data['kanji']}*: {rusnick} {extra_1}\n"
                            f"Онъёми: {kanji_data['onyomi'] if kanji_data['onyomi'] else 'нет/неизвестно'}\n"
                            + escape_markdown(readings_meanings) + "\n" + extra_2)

        if kanji_data['compounds']:

            await message.channel.send("Составные слова с этим кандзи:")

            if "1" in kanji_data['compounds_examples'].keys():

                if kanji_data['compound_meanings']:
                    for index, compound_meaning in enumerate(kanji_data['compound_meanings']):
                        compounds = [kanji_data['compounds'][com_index] for com_index in kanji_data['compounds_examples'][
                            str(index+1)]]
                        compounds = '\n'.join(
                            [compound['okurigana'] + " (" + compound["reading"].replace('*', '') + ")" +
                            " — " + Kanji.format_meaning(compound["Russian"]) for compound in compounds])
                        await message.channel.send(escape_markdown(str(compound_meaning + ':\n' + compounds)))
                else:
                    compounds = [kanji_data['compounds'][com_index] for com_index in kanji_data['compounds_examples'][
                        str(1)]]
                    compounds = '\n'.join(
                        [compound['okurigana'] + "(" + compound["reading"].replace('*', '') + ")"
                            + " — " + Kanji.format_meaning(compound["Russian"]) for compound in compounds])
                    await message.channel.send(escape_markdown(compounds))

                if nanori_nums := kanji_data['compounds_examples']['nanori']:
                    await message.channel.send("В именах и топологических названиях:")
                    nanori = [kanji_data['compounds'][nanori_num] for nanori_num in nanori_nums]
                    nanori = '\n'.join([compound['okurigana'] + "(" + compound["reading"].replace('*', '') + ")"
                                        + " — " + Kanji.format_meaning(compound["Russian"]) for compound in nanori])
                    await message.channel.send(escape_markdown(nanori))

            else:
                compounds = '\n'.join([compound['okurigana'] + "(" + compound["Reading"].replace('*', '') + ")"
                                    + " — " + Kanji.format_meaning(compound["Russian"]) for compound in
                                    kanji_data['compounds'].values()])
                await message.channel.send(escape_markdown(compounds))

        file = None
        if (gif := f"0_{kanji_data['Nomer']}.gif") in os.listdir("SOD"):
            file = File(f"SOD/{gif}")
        elif (gif := f"1_{kanji_data['Nomer']}.gif") in os.listdir("SOD"):
            file = File(f"SOD/{gif}")
        elif (gif := f"2_{kanji_data['Nomer']}.gif") in os.listdir("SOD"):
            file = File(f"SOD/{gif}")

        if file:
            await message.channel.send(file=file)
        else:
            await message.channel.send("Для этого кандзи нет диаграммы начертания")


@bot.tree.command(name="grades", description="Классы иероглифов")
async def ping_command(interaction: Interaction):
    text = escape_markdown("(1-10) класс - класс в школах Японии, в котором учат данный иероглиф\n"
            "+++ - иероглиф не включен в \"Дзёё кандзи\", но весьма употребим и вполне мог бы туда входить\n"
            "++ - иероглиф достаточно употребим и вероятно претендовал бы на попадание в список \"Дзёё кандзи\"\n"
            "+ - иероглиф не очень употребим, но знание его может пригодиться\n"
            "(++) - иероглиф как таковой малоупотребим, но весьма употребимо слово, которое он записывает "
            "(в современном японском языке для записи этого слова чаще используется кана\n"
            "(+) - иероглиф как таковой малоупотребим, но полезно знать слово, которое он записывает\n"
            "И ++ - иероглиф часто используется для записи имен собственных\n"
            "И + - иероглиф встречается в именах собственных\n"
            "+x - иероглиф малоупотребим, но все же встречается\n"
            "x - иероглиф малоупотребим и редок\n"
            "xx - иероглиф крайне редок\n"
            "xxx - иероглиф можно считать практически несуществующим\n"
            "Ф - форма или вариант другого иероглифа")
    await interaction.response.send_message(text)    


bot.run(token=DISCORD_BOT_TOKEN)
