import logging
import os
from kanji import Kanji
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InputFile

logging.basicConfig(level=logging.DEBUG)
AIOGRAM_API_TOKEN = os.environ.get("AIOGRAM_API_TOKEN")

bot = Bot(token=AIOGRAM_API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class KanjiSearch(StatesGroup):
    search = State()


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer(f"_Здравствуйте_, {message.from_user.full_name}\n\n"
                         f"Это бот по изучению кандзи на основе ЯРКСИ\. Разработчик: @korollzoilist\n\n"
                         f"Чтобы получить информацию о кандзи, введите команду /search\_kanji "
                         f"и введите иероглиф",
                         parse_mode='MarkdownV2')


@dp.message_handler(commands=["help"])
async def help_info(message: types.Message):
    await message.answer("На данный момент бот работает только на поиск иероглифов, в будущем планируется поиск "
                         "составных слов по кандзи, Хепберну и Поливанову.\nЕсли бот не отвечает в течение пятнадцати "
                         "секунд, перестал работать на полпути или информация отображается некорректно, "
                         "пишите @korollzoilist и отправьте кандзи, на котором бот завис")


@dp.message_handler(commands=["search_kanji"])
async def search_kanji(message: types.Message):

    await KanjiSearch.search.set()

    await message.answer("Введите кандзи")
    print(f'Ищет {message.from_user.full_name}')


@dp.message_handler(state="*", commands="cancel")
@dp.message_handler(Text(equals="отмена", ignore_case=True), state="*")
async def cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    logging.info(f"Collecting state {current_state}")
    await state.finish()
    await message.answer("Поиск кандзи отменен")
    print(f"{message.from_user.full_name} больше не ищет")


@dp.message_handler(state=KanjiSearch.search)
async def kanji_info(message: types.Message, state: FSMContext):
    def escape_markdown(text: str) -> str:
        escape_chars = ('_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!')
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        return text

    try:
        kanji = Kanji(message.text)
    except TypeError:
        await message.reply("Вы ввели больше одного символа")
        raise
    except ValueError:
        await message.reply("Это не кандзи")
        await message.answer("Пожалуйста, введите кандзи")
        raise
    else:
        await state.finish()
    print(kanji.get_info())

    kanji_data = kanji.get_info()

    rusnick = (escape_markdown(kanji_data['RusNick']) or
               "значение для этого кандзи отсутствует в базе данных или ещё не добавлено")
    readings_meanings = '\n'.join(kanji_data['readings_meanings'])

    await message.answer(f"{kanji_data['kanji']}: {rusnick}\n"
                         f"Онъёми: {kanji_data['onyomi'] if kanji_data['onyomi'] else 'нет/неизвестно'}\n"
                         + escape_markdown(readings_meanings), parse_mode='MarkdownV2')

    if kanji_data['compounds']:

        await message.answer("Составные слова с этим кандзи:")

        if "1" in kanji_data['compounds_examples'].keys():

            if kanji_data['compound_meanings']:
                for index, compound_meaning in enumerate(kanji_data['compound_meanings']):
                    compounds = [kanji_data['compounds'][com_index] for com_index in kanji_data['compounds_examples'][
                        str(index+1)]]
                    compounds = '\n'.join(
                        [compound['okurigana'] + "(" + compound["reading"].replace('*', '') + ")" +
                         " " + compound["Russian"] for compound in compounds])
                    await message.answer(escape_markdown(str(compound_meaning + ':\n' + compounds)),
                                         parse_mode='MarkdownV2')
            else:
                compounds = [kanji_data['compounds'][com_index] for com_index in kanji_data['compounds_examples'][
                    str(1)]]
                compounds = '\n'.join(
                    [compound['okurigana'] + "(" + compound["reading"].replace('*', '') + ")"
                        + " " + compound["Russian"] for compound in compounds])
                await message.answer(escape_markdown(compounds), parse_mode='MarkdownV2')

            if nanori_nums := kanji_data['compounds_examples']['nanori']:
                await message.answer("В именах и топологических названиях:")
                nanori = [kanji_data['compounds'][nanori_num] for nanori_num in nanori_nums]
                nanori = '\n'.join([compound['okurigana'] + "(" + compound["reading"].replace('*', '') + ")"
                                    + " " + compound["Russian"] for compound in nanori])
                await message.answer(escape_markdown(nanori), parse_mode='MarkdownV2')

        else:
            compounds = '\n'.join([compound['okurigana'] + "(" + compound["Reading"].replace('*', '') + ")"
                                   + " " + compound["Russian"] for compound in kanji_data['compounds'].values()])
            await message.answer(escape_markdown(compounds), parse_mode='MarkdownV2')

    file = None
    if (gif := f"0_{kanji_data['Nomer']}.gif") in os.listdir("SOD"):
        file = InputFile(f"SOD/{gif}")
    elif (gif := f"1_{kanji_data['Nomer']}.gif") in os.listdir("SOD"):
        file = InputFile(f"SOD/{gif}")
    elif (gif := f"2_{kanji_data['Nomer']}.gif") in os.listdir("SOD"):
        file = InputFile(f"SOD/{gif}")

    if file:
        await message.answer_animation(file)
    else:
        await message.answer("Для этого кандзи нет диаграммы начертания")


@dp.message_handler(commands='giveusatank')
async def daite_tank(message: types.Message):
    await message.answer("Вау. Видимо, Вы - человек высокой культуры.\nНапишите мне, поболтаем о группе и всяком")


@dp.message_handler()
async def echo(message: types.Message):
    await message.answer(message.text)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
