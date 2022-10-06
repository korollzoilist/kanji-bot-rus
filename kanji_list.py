import re
import sqlite3
import romkan


class Kanji:

    def __init__(self, kanji):
        self.con = sqlite3.connect("yarxi.db")
        self.cur = self.con.cursor()
        self.kanji = kanji
        self.chars = sorted([uncd[0] for uncd in self.cur.execute("SELECT Uncd FROM Kanji").fetchall()])

        if len(self.kanji) > 1:
            raise TypeError("There should only be one character")

        if not ord(self.kanji) in self.chars:
            raise ValueError("It is not kanji")

        self.info = self.cur.execute(f"SELECT * FROM kanji WHERE Uncd = {ord(self.kanji)}").fetchall()[0]

    def get_info(self) -> dict:
        info_dict = {}
        info_dict['kanji'] = self.kanji

        for column in self.cur.execute("PRAGMA table_info(Kanji)").fetchall():
            info_dict[column[1]] = self.info[column[0]]

        info_dict['compound_readings'] = []
        if compound_readings := re.findall(r"\|(\S+)\|*", info_dict['Kunyomi']):
            compound_readings = re.split(r"/", compound_readings[0])
            for compound_reading in compound_readings:
                info_dict['compound_readings'].append(Kanji.to_kana(compound_reading.lower()))

        info_dict['RusNick'] = Kanji.escape_chars(info_dict['RusNick'].replace('#', ', ').replace('*', ''))

        if info_dict['Onyomi'] != "-":
            onyomis = re.split(r',', info_dict['Onyomi'])
            onyomis = ','.join([Kanji.to_kana(onyomi.replace('*', '').replace(
                '-', 'кокудзи '), is_onyomi=True) for onyomi in onyomis])
            info_dict['onyomi'] = onyomis
        else:
            info_dict['onyomi'] = 'кокудзи'

        info_dict['compounds'] = {}

        for compound in self.cur.execute(f"SELECT * FROM Tango WHERE (K1 = {info_dict['Nomer']}) or \
                                           (K2 = {info_dict['Nomer']}) or (K3 = {info_dict['Nomer']}) or \
                                           (K4 = {info_dict['Nomer']})"
                                         f"or Kana LIKE '%#{info_dict['Nomer']}#%'").fetchall():
            info_dict['compounds'][compound[0]] = {}
            for column in self.cur.execute("PRAGMA table_info(Tango)").fetchall():
                info_dict['compounds'][compound[0]][column[1]] = compound[column[0]]

            info_dict['compounds'][compound[0]]['Russian'] = self.adjust_meaning(
                info_dict['compounds'][compound[0]]['Russian'])

            info_dict['compounds'][compound[0]]['okurigana'] = self.add_okurigana(
                info_dict['compounds'][compound[0]]['Nomer'])

            info_dict['compounds'][compound[0]]['reading'] = Kanji.to_kana(
                info_dict['compounds'][compound[0]]['Reading'])

        info_dict["readings_meanings"] = []
        for example in info_dict['compounds'].values():
            if example['K2'] == 0 and example['K3'] == 0 and example['K4'] == 0:
                reading = example["Reading"]
                meaning = self.adjust_meaning(example['Russian'])
                if example["Kana"]:
                    if example["Kana"][0] != "0":
                        okurigana = re.findall(r"[1-4](.+)", example["Kana"])[0]
                        if "*" in reading:
                            index = reading.index("*")
                            reading = reading[:index]
                        if "^" in okurigana:
                            okurigana, k_okurigana = re.split(r"\^", okurigana)
                            reading = Kanji.to_kana(reading[:-len(okurigana + k_okurigana)]) + '\.' + Kanji.to_kana(
                                okurigana) + \
                                      Kanji.to_kana(k_okurigana, is_katakana=True)
                        else:
                            if "qi" in okurigana:
                                okurigana = okurigana[2:]
                                if okurigana:
                                    reading = Kanji.to_kana(
                                        reading[:-len(okurigana)]) + '\.々' + Kanji.to_kana(okurigana)
                                else:
                                    reading = Kanji.to_kana(reading) + "\.々"
                            else:
                                reading = Kanji.to_kana(reading[:-len(okurigana)]) + '\.' + Kanji.to_kana(okurigana)

                        info_dict["readings_meanings"].append(reading + "\n" + meaning)

                else:
                    reading = Kanji.to_kana(reading)
                    info_dict["readings_meanings"].append(reading + "\n" + meaning)

        try:
            meanings, compound_meanings = re.split(r'\|', info_dict['Russian'])
        except ValueError:
            compound_meanings = [meaning.replace('\\', '').replace('/', '') for meaning in re.findall(
                r"([\S\s.#;][^/]*)", info_dict['Russian'])]
            info_dict['compound_meanings'] = []
            for compound_meaning in compound_meanings:
                if nums := re.findall(r"\((\d+)\)", compound_meaning):
                    for num in nums:
                        compound_meaning = compound_meaning.replace(num,
                                                                    info_dict['compound_readings'][int(num) - 1])
                compound_meaning = self.adjust_meaning(compound_meaning)
                info_dict['compound_meanings'].append(compound_meaning.capitalize())
        else:
            compound_meanings = [compound_meaning.replace('\\', '').replace('/', '') for compound_meaning in re.findall(
                r"([\S\s.#;][^/]*)", compound_meanings)]
            info_dict['compound_meanings'] = []
            for compound_meaning in compound_meanings:
                if nums := re.findall(r"\((\d+)\)", compound_meaning):
                    for num in nums:
                        compound_meaning = compound_meaning.replace(num, info_dict['compound_readings'][int(num) - 1])
                compound_meaning = self.adjust_meaning(compound_meaning)
                info_dict['compound_meanings'].append(compound_meaning.capitalize())

        compounds_examples = re.split(r',', info_dict['Compounds'].replace(
            '#', '').replace('*', '').replace('^', '').replace('&', '').replace("@", ""))

        info_dict['compounds_examples'] = {}
        info_dict['compounds_examples']['nanori'] = []
        if info_dict['Compounds'] and info_dict['Nomer'] not in (4742, 5051, 5526):
            for compound_example in compounds_examples:
                num, example = re.split(r':', compound_example)
                try:
                    example = int(example)
                except ValueError:
                    pass

                match num:
                    case "N":
                        info_dict['compounds_examples']["nanori"].append(example)
                    case _:
                        try:
                            info_dict['compounds_examples'][num].append(example)
                        except KeyError:
                            info_dict['compounds_examples'][num] = []
                            info_dict['compounds_examples'][num].append(example)

        return info_dict

    @staticmethod
    def to_kana(reading: str, is_katakana=False, is_onyomi=False) -> str:
        if reading:
            reading = re.findall(r"([a-zа-я:;,/\- ]+)(?=\*\(\*)*", reading)[0].replace(
                'nn', 'nnn').replace("Q1", "").replace('qi', '々')
            word = ""
            prev_symbol = None
            if is_katakana:
                for symbol in reading:
                    match symbol:
                        case ":":
                            word += "ー"
                        case _:
                            word += symbol

                word = romkan.to_kunrei(word)
                if word[-1] == romkan.to_katakana(word)[-1] and word[-1] != "々":
                    word = word[:-1] + "ッ"

                return romkan.to_katakana(word)
            elif is_onyomi:
                for symbol in reading:
                    match symbol:
                        case ":":
                            match prev_symbol:
                                case "o":
                                    word += "u"
                                case _:
                                    word += prev_symbol
                        case _:
                            word += symbol

                    prev_symbol = symbol

                word = romkan.to_kunrei(word)
                return Kanji.escape_chars(romkan.to_katakana(word))
            else:
                for symbol in reading:
                    match symbol:
                        case ":":
                            match prev_symbol:
                                case "o":
                                    word += "u"
                                case _:
                                    word += prev_symbol
                        case _:
                            word += symbol

                    prev_symbol = symbol

                word = romkan.to_kunrei(word)
                if word[-1] == romkan.to_hiragana(word)[-1] and not re.findall(r"[々*]", word):
                    word = word[:-1] + "っ"

                return Kanji.escape_chars(romkan.to_hiragana(word))

        return ""

    @staticmethod
    def escape_chars(text: str) -> str:
        escaped_chars = ('*', '~', '-', '.', '(', ')', '[', ']', '>', '!', '#')
        for char in escaped_chars:
            text = text.replace(char, '\\'+char)

        return text

    def adjust_meaning(self, meaning: str) -> str:
        meaning = meaning.replace('\\', '').replace('$', '').replace('_', '')
        if meaning.startswith(">>"):
            words = re.findall(r"^(\S+)", meaning) + re.findall(r"г\.(\S+)", meaning)
            for word in words:
                meaning = meaning.replace(word, word.capitalize())
        if nomers := re.findall(r"\((!\d+)\)", meaning):
            for nomer in nomers:
                meaning = meaning.replace(nomer, '')
        if "_" in meaning:
            meaning = meaning.replace('_', '')
        if "&" in meaning:
            count = 1
            index = meaning.index('&')
            meaning = meaning[:index] + str(count) + " " + meaning[index + 1:]
            count += 1
            while "&" in meaning:
                index = meaning.index('&')
                if meaning[index + 1] == '&':
                    meaning = meaning[:index] + "\n" + str(count) + " " + meaning[index + 2:]
                else:
                    meaning = meaning[:index] + "\n" + str(count) + " " + meaning[index + 1:]
                count += 1
        if nomers := re.findall(r"\^(\d)-(\d+)", meaning):
            is_0, is_1, is_3, is_4, is_5 = False, False, False, False, False
            for digit_nomer in nomers:
                digit, nomer = digit_nomer
                char = chr(self.cur.execute(f'SELECT Uncd FROM Kanji WHERE Nomer = {nomer}').fetchone()[0])
                match digit:
                    case "0":
                        if is_0:
                            meaning = meaning.replace(f'^{digit}-{nomer}', f', {char}')
                        else:
                            meaning = meaning.replace(f'^{digit}-{nomer}', f' См. {char}')
                    case "1":
                        if is_1:
                            meaning = meaning.replace(f'^{digit}-{nomer}', f', {char}')
                        else:
                            meaning = meaning.replace(f'^{digit}-{nomer}', f' Ср. {char}')
                            is_1 = True
                    case "3":
                        if is_3:
                            meaning = meaning.replace(f'^{digit}-{nomer}', f', {char}')
                        else:
                            meaning = meaning.replace(f'^{digit}-{nomer}', f'; реже {char}')
                            is_3 = True
                    case "4":
                        if is_4:
                            meaning = meaning.replace(f'^{digit}-{nomer}', f', {char}')
                        else:
                            meaning = meaning.replace(f'^{digit}-{nomer}', f'; иначе {char}')
                            is_4 = True
                    case "5":
                        if is_5:
                            meaning = meaning.replace(f'^{digit}-{nomer}', f', {char}')
                        else:
                            meaning = meaning.replace(f'^{digit}-{nomer}', f'; чаще {char}')
                            is_5 = True
        if digit_nomers := re.findall(r"\{\^\^(\d)(\d+)(.*)}", meaning):
            is_1, is_7 = False, False
            for digit, nomer, info in digit_nomers:
                char = chr(self.cur.execute(f"SELECT Uncd FROM Kanji WHERE Nomer = {nomer}").fetchone()[0])
                match digit:
                    case "1":
                        if is_1:
                            meaning = meaning.replace('{^^' + digit + nomer + info + '}', f', {char + info}')
                        else:
                            meaning = meaning.replace('{^^' + digit + nomer + info + '}', f'; ср. {char + info}')
                            is_1 = True
                    case "7":
                        if is_7:
                            meaning = meaning.replace('{^^' + digit + nomer + info + '}', f', {char + info}')
                        else:
                            meaning = meaning.replace('{^^' + digit + nomer + info + '}', f'; антоним: {char + info}')
                            is_7 = True
        if word_noms := re.findall(r"\^+(\d)(\d+)", meaning):
            is_0, is_1, is_3, is_4, is_5, is_6, is_7 = False, False, False, False, False, False, False
            for digit_word_nom in word_noms:
                digit, word_nom = digit_word_nom
                word = self.add_okurigana(word_nom)
                reading = self.cur.execute(
                    f"SELECT Reading FROM Tango WHERE Nomer = {int(word_nom)}").fetchone()[0]
                word_reading = Kanji.to_kana(re.findall(r"^(.*)\**", reading)[0])
                match len(re.findall(rf"(\^+){digit + word_nom}", meaning)):
                    case 1:
                        match digit:
                            case "0":
                                if is_0:
                                    meaning = meaning.replace(f'^{digit + word_nom}', f', {word}({word_reading})')
                                else:
                                    meaning = meaning.replace(f'^{digit + word_nom}', f' См. {word}({word_reading})')
                            case "1":
                                if is_1:
                                    meaning = meaning.replace(f'^{digit + word_nom}', f', {word}({word_reading})')
                                else:
                                    meaning = meaning.replace(f'^{digit + word_nom}', f' Ср. {word}({word_reading})')
                                    is_1 = True
                            case "3":
                                if is_3:
                                    meaning = meaning.replace(f'^{digit + word_nom}', f', {word}({word_reading})')
                                else:
                                    meaning = meaning.replace(f'^{digit + word_nom}', f'; реже {word}({word_reading})')
                                    is_3 = True
                            case "4":
                                if is_4:
                                    meaning = meaning.replace(f'^{digit + word_nom}', f', {word}({word_reading})')
                                else:
                                    meaning = meaning.replace(f'^{digit + word_nom}', f'; иначе {word}({word_reading})')
                                    is_4 = True
                            case "5":
                                if is_5:
                                    meaning = meaning.replace(f'^{digit + word_nom}', f', {word}({word_reading})')
                                else:
                                    meaning = meaning.replace(f'^{digit + word_nom}', f'; чаще {word}({word_reading})')
                                    is_5 = True
                            case "6":
                                if is_6:
                                    meaning = meaning.replace(f'^{digit + word_nom}', f', {word}({word_reading})')
                                else:
                                    meaning = meaning.replace(
                                        f'^{digit + word_nom}', f'; синоним: {word}({word_reading})')
                                    is_6 = True
                            case "7":
                                if is_7:
                                    meaning = meaning.replace(f'^{digit + word_nom}', f', {word}({word_reading})')
                                else:
                                    meaning = meaning.replace(
                                        f'^{digit + word_nom}', f'; антоним: {word}({word_reading})')
                                    is_7 = True
                    case 2:
                        meaning = meaning.replace(f'^^{digit + word_nom}', f'; сокр. от {word}')
        if "qi" in meaning:
            meaning = meaning.replace('qi', '々')
        if "^^" in meaning:
            meaning = meaning.replace("^^", " (чаще хираганой)")
        if "^@" in meaning:
            meaning = meaning.replace("^@", " (чаще катаканой)")
        if kanas := re.findall(r"''([a-z^]+)''", meaning):
            for kana in kanas:
                if "^" in kana:
                    meaning = meaning.replace(f"''{kana}''", Kanji.to_kana(kana, is_katakana=True))
                else:
                    meaning = meaning.replace(f"''{kana}''", Kanji.to_kana(kana))
        if "*1" in meaning:
            meaning = meaning.replace('*1', '~する ')
        if "*2" in meaning:
            meaning = meaning.replace('*2', '~な ')
        if "*3" in meaning:
            meaning = meaning.replace('*3', '~の ')
        if "*4" in meaning:
            meaning = meaning.replace('*4', '~に ')
        if "*5" in meaning:
            meaning = meaning.replace('*5', '~で ')
        if "*6" in meaning:
            meaning = meaning.replace('*6', '~と ')
        if "*8" in meaning:
            meaning = meaning.replace('*8', '~して ')
        if "*=05" in meaning:
            meaning = meaning.replace('*=05', '~がしてある')
        if "*=06" in meaning:
            meaning = meaning.replace('*=06', '~がする')
        if "*=10" in meaning:
            meaning = meaning.replace('*=10', '~で (~に)')  # какой же идиотизм... можно же сделать '*5(*4)',
            # чтоб потом вместо '*=30' написать '*4(*5)'
        if "*=21" in meaning:
            meaning = meaning.replace('*=21', '~な(~の)')  # а нельзя было сделать '*2 (*3)'???
        if "*=23" in meaning:
            meaning = meaning.replace('*=23', '~ならず ')
        if "*=26" in meaning:
            meaning = meaning.replace('*=26', '~なしの')
        if "*=28" in meaning:
            meaning = meaning.replace('*=28', '~なく ')
        if "*=29" in meaning:
            meaning = meaning.replace('*=29', '~に (~は)')
        if "*=30" in meaning:
            meaning = meaning.replace('*=30', '~に (~で)')
        if "*=31" in meaning:
            meaning = meaning.replace('*=31', '~にも')
        if "*=32" in meaning:
            meaning = meaning.replace('*=32', '~的(てき)　')
        if "*=33" in meaning:
            meaning = meaning.replace('*=33', '~にして')
        if "*=46" in meaning:
            meaning = meaning.replace('*=46', '~のした ')
        if "*=47" in meaning:
            meaning = meaning.replace('*=47', '~のしない ')
        if "*=48" in meaning:
            meaning = meaning.replace('*=48', '~のする ')
        if "*=53" in meaning:
            meaning = meaning.replace('*=53', '~をやる ')
        if "*=62" in meaning:
            meaning = meaning.replace('*=62', '~となる ')
        if "*=84" in meaning:
            meaning = meaning.replace('*=84', '~をして ')
        if "**0" in meaning:
            meaning = meaning.replace("**0", "~をする ")
        if "**1" in meaning:
            meaning = meaning.replace('**1', '~がある ')
        if "**2" in meaning:
            meaning = meaning.replace('**2', '~のある ')
        if "**3" in meaning:
            meaning = meaning.replace('**3', '~のない ')
        if "**4" in meaning:
            meaning = meaning.replace('**4', '~である ')
        if "**6" in meaning:
            meaning = meaning.replace('**6', '~だ')
        if "**7" in meaning:
            meaning = meaning.replace('**7', '~にする ')
        if "**8" in meaning:
            meaning = meaning.replace('**8', '~になる ')
        if "**9" in meaning:
            meaning = meaning.replace('**9', '~として ')
        if "***7" in meaning:
            meaning = meaning.replace('***7', '~がしている ')
        if "*-3" in meaning:
            meaning = meaning.replace('*-3', ' (-の)')
        if "*-7" in meaning:
            meaning = meaning.replace('*-7', ' (-を)')
        if "#" in meaning:
            meaning = meaning.replace('#', '_ ')
        if "@0" in meaning:
            meaning = meaning.replace('@0', '_употребляется фонетически_')
        if "@3" in meaning:
            meaning = meaning.replace('@3', ' и т.д.')
        if "@4" in meaning:
            meaning = meaning.replace('@4', 'В сочетаниях непродуктивен')
        if "@6" in meaning:
            meaning = meaning.replace('@6', 'в сочетаниях то же')
        if "@" in meaning:
            meaning = meaning.replace("@", "")
        if "=" in meaning:
            meaning = meaning.replace("=", " ")
        if "{" in meaning:
            meaning = meaning.replace('{', '')
        if "}" in meaning:
            meaning = meaning.replace('}', '')
        if "+" in meaning:
            meaning = meaning.replace('+', '')
        if ">1" in meaning:
            meaning = meaning.replace('>1', '_мужское имя_')
        if ">2" in meaning:
            meaning = meaning.replace('>2', '_женское имя_')
        if ">3" in meaning:
            meaning = meaning.replace('>3', '_фамилия_')
        if ">4" in meaning:
            meaning = meaning.replace('>4', '_псевдоним_')
        if ">5" in meaning:
            meaning = meaning.replace('>5', '_топоним_')

        return Kanji.escape_chars(meaning)

    def add_kanji(self, kana: str) -> tuple:
        nomers = re.findall(r"#(\d+)#", kana)
        kanjis = [chr(
            self.cur.execute(f"SELECT Uncd FROM Kanji WHERE Nomer = {kanji}").fetchone()[0]) for kanji in nomers]
        return nomers, kanjis

    def add_okurigana(self, word_nom: str) -> str:
        word = ""
        k_1, k_2, k_3, k_4, kana = self.cur.execute(
            f"SELECT K1, K2, K3, K4, Kana FROM Tango WHERE Nomer = {int(word_nom)}").fetchone()
        kanjis = ''.join([chr(
            self.cur.execute(f"SELECT Uncd FROM Kanji WHERE Nomer = {kanji}").fetchone()[0]) for kanji in [
            k_1, k_2, k_3, k_4] if kanji != 0 and kanji != -1])
        if kanjis:
            if "#" in kana:
                nomers, extra_kanjis = self.add_kanji(kana)
                kanjis += ''.join(extra_kanjis)
                for nomer in nomers:
                    kana = kana.replace(f"#{nomer}#", '')
            okuriganas = {int(num): Kanji.to_kana(
                okurigana) for num, okurigana in re.findall(r"(\d)([a-z]+)", kana)}
            word = kanjis
            for num, kanji in enumerate(kanjis):
                if num + 1 in okuriganas.keys():
                    word = word.replace(kanji, kanji + okuriganas[num + 1])
        elif kana:
            word = Kanji.to_kana(kana)

        return Kanji.escape_chars(word)

    def __del__(self):
        self.con.close()
