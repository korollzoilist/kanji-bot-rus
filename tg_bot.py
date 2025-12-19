import logging
import os
from kanji import Kanji
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types.input_file import FSInputFile
from aiogram.filters import Command, CommandStart


load_dotenv()
AIOGRAM_API_TOKEN = os.getenv("AIOGRAM_API_TOKEN")
tg_bot = Bot(token=AIOGRAM_API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher()
router = Router()
dp.include_router(router)


class KanjiSearch(StatesGroup):
    search = State()


def escape_markdown(text: str) -> str:
    escape_chars = ('_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!')
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text


@router.message(CommandStart())
async def start(message: types.Message):
    text = escape_markdown(f"Здравствуйте, {message.from_user.full_name}\n\n"
                           f"Это бот по изучению кандзи на основе ЯРКСИ. Разработчик: @korollzoilist\n\n"
                           f"Чтобы получить информацию о кандзи, введите команду /search_kanji "
                           f"и введите иероглиф")
    await message.answer(text, parse_mode='MarkdownV2')


@router.message(Command("help"))
async def help_info(message: types.Message):
    text = escape_markdown("На данный момент бот работает только на поиск иероглифов, в будущем планируется поиск "
                           "составных слов по кандзи, Хепберну и Поливанову.\nЕсли бот не отвечает в течение пятнадцати "
                           "секунд, перестал работать на полпути или информация отображается некорректно, "
                           "пишите @korollzoilist и отправьте кандзи, на котором бот завис")
    await message.answer(text)


@router.message(Command("search_kanji"))
async def search_kanji(message: types.Message, state: FSMContext):

    await state.set_state(KanjiSearch.search)

    await message.answer("Введите кандзи")
    print(f'Ищет {message.from_user.full_name}')


@router.message(Command("cancel"))
@router.message(F.text.lower()=="отмена")
async def cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    logging.info(f"Collecting state {current_state}")
    await state.clear()
    await message.answer("Поиск кандзи отменен")
    print(f"{message.from_user.full_name} больше не ищет")


@router.message(KanjiSearch.search)
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
        await state.clear()

    kanji_data = kanji.get_info()

    print(kanji_data)

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

    await message.answer(f"{grade}\n*{kanji_data['kanji']}*: {rusnick} {extra_1}\n"
                         f"Онъёми: {kanji_data['onyomi'] if kanji_data['onyomi'] else 'нет/неизвестно'}\n"
                         + escape_markdown(readings_meanings) + "\n" + extra_2, parse_mode='MarkdownV2')

    if kanji_data['compounds']:

        await message.answer("Составные слова с этим кандзи:")

        if "1" in kanji_data['compounds_examples'].keys():

            if kanji_data['compound_meanings']:
                for index, compound_meaning in enumerate(kanji_data['compound_meanings']):
                    compounds = [kanji_data['compounds'][com_index] for com_index in kanji_data['compounds_examples'][
                        str(index+1)]]
                    compounds = '\n'.join(
                        [compound['okurigana'] + " (" + compound["reading"].replace('*', '') + ")" +
                         " — " + Kanji.format_meaning(compound["Russian"]) for compound in compounds])
                    await message.answer(escape_markdown(str(compound_meaning + ':\n' + compounds)),
                                         parse_mode='MarkdownV2')
            else:
                compounds = [kanji_data['compounds'][com_index] for com_index in kanji_data['compounds_examples'][
                    str(1)]]
                compounds = '\n'.join(
                    [compound['okurigana'] + "(" + compound["reading"].replace('*', '') + ")"
                        + " — " + Kanji.format_meaning(compound["Russian"]) for compound in compounds])
                await message.answer(escape_markdown(compounds), parse_mode='MarkdownV2')

            if nanori_nums := kanji_data['compounds_examples']['nanori']:
                await message.answer("В именах и топологических названиях:")
                nanori = [kanji_data['compounds'][nanori_num] for nanori_num in nanori_nums]
                nanori = '\n'.join([compound['okurigana'] + "(" + compound["reading"].replace('*', '') + ")"
                                    + " — " + Kanji.format_meaning(compound["Russian"]) for compound in nanori])
                await message.answer(escape_markdown(nanori), parse_mode='MarkdownV2')

        else:
            compounds = '\n'.join([compound['okurigana'] + "(" + compound["Reading"].replace('*', '') + ")"
                                   + " — " + Kanji.format_meaning(compound["Russian"]) for compound in
                                   kanji_data['compounds'].values()])
            await message.answer(escape_markdown(compounds), parse_mode='MarkdownV2')

    file = None
    if (gif := f"0_{kanji_data['Nomer']}.gif") in os.listdir("SOD"):
        file = FSInputFile(f"SOD/{gif}")
    elif (gif := f"1_{kanji_data['Nomer']}.gif") in os.listdir("SOD"):
        file = FSInputFile(f"SOD/{gif}")
    elif (gif := f"2_{kanji_data['Nomer']}.gif") in os.listdir("SOD"):
        file = FSInputFile(f"SOD/{gif}")

    if file:
        await message.answer_animation(file)
    else:
        await message.answer("Для этого кандзи нет диаграммы начертания")


@router.message(Command('grades'))
async def grades(message: types.Message):
    text = escape_markdown("(1-10) класс - класс в школах Японии, в котором учат данный иероглиф\n"
            "+++ - иероглиф не включен в \"Дзёё кандзи\", но весьма употребим и вполне мог бы туда входить\n"
            "++ - иероглиф достаточно употребим и вероятно претендовал бы на попадание в список \"Дзёё кандзи\"\n"
            "+ - иероглиф не очень употребим, но знание его может пригодиться\n"
            "(++) - иероглиф как таковой малоупотребим, но весьма употребимо слово, которое он записывает "
            "(в современном японском языке для записи этого слова чаще используется кана\n"
            "(+) - иероглиф как таковой малоупотребим, но полезно знать слово, которое он записывает\n"
            "И ++ - иероглиф часто используется для записи имен собственных\n"
            "И + - иероглиф встречается в именах собственных\n"
            "+\\x - иероглиф малоупотребим, но все же встречается\n"
            "x - иероглиф малоупотребим и редок\n"
            "xx - иероглиф крайне редок\n"
            "xxx - иероглиф можно считать практически несуществующим\n"
            "Ф - форма или вариант другого иероглифа")
    await message.answer(text, parse_mode='MarkdownV2')


@router.message(Command('giveusatank'))
async def daite_tank(message: types.Message):
    await message.answer("Вау. Видимо, Вы - человек высокой культуры.\nНапишите мне, поболтаем о группе и всяком")


@router.message()
async def echo(message: types.Message):
    await message.answer(escape_markdown(message.text))
