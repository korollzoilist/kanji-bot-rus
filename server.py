import logging
import os
from kanji import Kanji
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InputFile
from aiogram.utils.executor import start_webhook

logging.basicConfig(level=logging.INFO)
AIOGRAM_API_TOKEN = os.environ.get("AIOGRAM_API_TOKEN")
WEBHOOK_URL = os.getenv('CYCLIC_URL', 'http://localhost:8181') + "/webhook/"
WEBHOOK_PATH = "/webhook/"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = 3001


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
    kakijun = kanji_data['SodKakijun']

    readings_meanings = '\n'.join(kanji_data['readings_meanings'])

    await message.answer(f"{kanji_data['kanji']}: {kanji_data['RusNick']}\n"
                         f"Онъёми: {kanji_data['onyomi']}\n"
                         + readings_meanings, parse_mode='MarkdownV2')

    if kanji_data['compounds']:

        await message.answer("Составные слова с этим кандзи:")

        if "1" in kanji_data['compounds_examples'].keys():

            if kanji_data['compound_meanings']:
                for index, compound_meaning in enumerate(kanji_data['compound_meanings']):
                    compounds = [kanji_data['compounds'][com_index] for com_index in kanji_data['compounds_examples'][
                        str(index+1)]]
                    compounds = '\n'.join(
                        [compound['okurigana'] + "\(" + compound["reading"].replace('*', '') + "\)" +
                         " " + compound["Russian"] for compound in compounds])
                    await message.answer(str(compound_meaning + ':\n' + compounds), parse_mode='MarkdownV2')
            else:
                compounds = [kanji_data['compounds'][com_index] for com_index in kanji_data['compounds_examples'][
                    str(1)]]
                compounds = '\n'.join(
                    [compound['okurigana'] + "\(" + compound["reading"].replace('*', '') + "\)"
                        + " " + compound["Russian"] for compound in compounds])
                await message.answer(compounds, parse_mode='MarkdownV2')

            if nanori_nums := kanji_data['compounds_examples']['nanori']:
                await message.answer("В именах и топологических названиях:")
                nanori = [kanji_data['compounds'][nanori_num] for nanori_num in nanori_nums]
                nanori = '\n'.join([compound['okurigana'] + "\(" + compound["reading"].replace('*', '') + "\)"
                                    + " " + compound["Russian"] for compound in nanori])
                await message.answer(nanori, parse_mode='MarkdownV2')

        else:
            compounds = '\n'.join([compound['okurigana'] + "\(" + compound["Reading"].replace('*', '') + "\)"
                                   + " " + compound["Russian"] for compound in kanji_data['compounds'].values()])
            await message.answer(compounds, parse_mode='MarkdownV2')

    file = None
    if (gif := f"0_{kanji_data['Nomer']}.gif") in os.listdir("SOD"):
        file = InputFile(f"SOD/{gif}")
    elif (gif := f"1_{kanji_data['Nomer']}.gif") in os.listdir("SOD"):
        file = InputFile(f"SOD/{gif}")
    elif (gif := f"2_{kanji_data['Nomer']}.gif") in os.listdir("SOD"):
        file = InputFile(f"SOD/{gif}")

    await message.answer_animation(file)


@dp.message_handler(commands='giveusatank')
async def daite_tank(message: types.Message):
    await message.answer("Вау. Видимо, Вы - человек высокой культуры.\nНапишите мне, поболтаем о группе и всяком")


@dp.message_handler()
async def echo(message: types.Message):
    await message.answer(message.text)


async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)


async def on_shutdown():
    logging.warning('Shutting down..')
    await bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()


start_webhook(
            dispatcher=dp,
            webhook_path=WEBHOOK_PATH,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            skip_updates=True,
            host=WEBAPP_HOST,
            port=WEBAPP_PORT,
    )