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
            raise TypeError("Не более одного символа")

        if not ord(self.kanji) in self.chars:
            raise ValueError("Это не кандзи")

        self.info = self.cur.execute(f"SELECT * FROM kanji WHERE Uncd = {ord(self.kanji)}").fetchall()[0]

    def get_info(self) -> dict:
        info_dict = {}
        info_dict['kanji'] = self.kanji

        for column in self.cur.execute("PRAGMA table_info(Kanji)").fetchall():
            info_dict[column[1]] = self.info[column[0]]

        info_dict['compound_readings'] = []
        if compound_readings := re.findall(r"\|([1-9a-z:,/_\- ]+)\|*", info_dict['Kunyomi'], re.IGNORECASE):
            compound_readings = re.split(r"/", compound_readings[0])
            for compound_reading in compound_readings:
                if compound_reading != 'Q1':
                    info_dict['compound_readings'].append(
                        Kanji.to_kana(compound_reading.replace(' ', '').replace('_', ', реже ').lower()))
        elif compound_readings := re.findall(r"\*([1-9a-z:,_\- ]+)\*", info_dict['Kunyomi'], re.IGNORECASE):
            for compound_reading in compound_readings:
                if compound_reading != 'Q1':
                    info_dict['compound_readings'].append(
                        Kanji.to_kana(compound_reading.replace(' ', '').replace('_', ', реже ').lower()))

        info_dict['RusNick'] = info_dict['RusNick'].replace('#', ', ').replace('*', '')

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

            info_dict['compounds'][compound[0]]['okurigana'] = self.add_okurigana(
                int(info_dict['compounds'][compound[0]]['Nomer']))

            info_dict['compounds'][compound[0]]['reading'] = Kanji.to_kana(
                info_dict['compounds'][compound[0]]['Reading'])

            info_dict['compounds'][compound[0]]['Russian'] = self.adjust_meaning(
                info_dict['compounds'][compound[0]]['Russian'])

        info_dict["readings_meanings"] = []
        for example in info_dict['compounds'].values():
            if example['K2'] == 0 and example['K3'] == 0 and example['K4'] == 0:
                reading = example["Reading"]
                meaning = example['Russian']
                if example["Kana"]:
                    if example["Kana"][0] != "0":
                        okurigana = re.findall(r"[1-4](.+)", example["Kana"])[0]
                        if "*" in reading:
                            index = reading.index("*")
                            reading = reading[:index]
                        if "^" in okurigana:
                            okurigana, k_okurigana = re.split(r"\^", okurigana)
                            reading = Kanji.to_kana(reading[:-len(okurigana + k_okurigana)]) + '.' + Kanji.to_kana(
                                okurigana) + \
                                      Kanji.to_kana(k_okurigana, is_katakana=True)
                        else:
                            if "qi" in okurigana:
                                okurigana = okurigana[2:]
                                if okurigana:
                                    reading = Kanji.to_kana(
                                        reading[:-len(okurigana)]) + '.々' + Kanji.to_kana(okurigana)
                                else:
                                    reading = Kanji.to_kana(reading) + ".々"
                            else:
                                reading = Kanji.to_kana(reading[:-len(okurigana)]) + "." + Kanji.to_kana(okurigana)

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
                    if "0" in nums:
                        compound_meaning = compound_meaning.replace("(0)", info_dict['compound_readings'][0])
                    else:
                        for num in nums:
                            compound_meaning = compound_meaning.replace(f"({num})",
                                                                        "\(" +
                                                                        info_dict['compound_readings'][int(num) - 1] +
                                                                        "\)")
                if len(info_dict['compounds']) != 1:
                    compound_meaning = self.adjust_meaning(compound_meaning)
                    info_dict['compound_meanings'].append(compound_meaning.capitalize())
        else:
            compound_meanings = [compound_meaning.replace('\\', '').replace('/', '') for compound_meaning in re.findall(
                r"([\S\s.#;][^/]*)", compound_meanings)]
            info_dict['compound_meanings'] = []
            for compound_meaning in compound_meanings:
                if nums := re.findall(r"\((\d+)\)", compound_meaning):
                    if "0" in nums:
                        compound_meaning = compound_meaning.replace("(0)", f"({info_dict['compound_readings'][0]})")
                    else:
                        for num in nums:
                            compound_meaning = compound_meaning.replace(f"({num})",
                                                                        "(" +
                                                                        info_dict['compound_readings'][int(num) - 1] +
                                                                        ")")
                if len(info_dict['compounds']) != 1:
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

        '''for key in [
            "Kunyomi", "Onyomi", "Kana", "Compounds", "Russian", "Reading",
            "Comp", "Nomer", "RusNick", "SodKakijun"
        ]:
            info_dict.pop(key, None)'''

        return info_dict

    @staticmethod
    def to_kana(reading: str, is_katakana=False, is_onyomi=False) -> str:
        if reading:
            reading = re.findall(r"([a-zа-я:;,/\- ()\[\]]+)(?=\*\(\*)*", reading)[0].replace(
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
                if word[-1] == romkan.to_katakana(word)[-1] and not re.findall(r"[々*()\[\]]", word):
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
                return romkan.to_katakana(word)
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
                if word[-1] == romkan.to_hiragana(word)[-1] and not re.findall(r"[々*()\[\]]", word):
                    word = word[:-1] + "っ"

                return romkan.to_hiragana(word)

        return ""


    def adjust_meaning(self, meaning: str) -> str:
        meaning = meaning.replace('\\', '').replace('$', '').replace('#', '_')
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
            is_0, is_1, is_2, is_3, is_4, is_5, is_6, is_7 = False, False, False, False, False, False, False, False
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
                            case "2":
                                if is_2:
                                    meaning = meaning.replace(f'^{digit + word_nom}', f', {word}({word_reading})')
                                else:
                                    meaning = meaning.replace(
                                        f'^{digit + word_nom}', f' то же, что и {word}({word_reading})')
                                    is_2 = True
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
        triple_asterisk_dict = {'***0': '~なる ',
                                '***1': '~から',
                                '***2': '~まで ',
                                '***3': '~[も',
                                '***4': '~[に',
                                '***5': '~とする ',
                                '***6': '~より ',
                                '***7': '~がしている ',
                                '***8': '~とした　',
                                '***9': '~としている '}

        double_asterisk_dict = {'**0': '~をする ',
                                '**1': '~がある ',
                                '**2': '~のある ',
                                '**3': '~のない ',
                                '**4': '~である ',
                                '**5': '~です',
                                '**6': '~だ',
                                '**7': '~にする ',
                                '**8': '~になる ',
                                '**9': '~として '}

        asterisk_hyphen_dict = {'*-0': '(は) ',
                                '*-1': '(から) ',
                                '*-3': ' (-の) ',
                                '*-4': '~(に) ',
                                '*-5': '(で) ',
                                '*-6': '(-と) ',
                                '*-7': ' (-を) ',
                                '*-8': '(-が) ',
                                '*-9': '(する) '}

        asterisk_equal_dict = {'*=00': '~! ',
                               '*=01': '~ある ',
                               '*=02': '~あって ',
                               '*=03': '~がない ',
                               '*=04': '~があって ',
                               '*=05': '~がしてある ',
                               '*=06': '~がする ',
                               '*=07': '~でも ',
                               '*=08': '~では ',
                               '*=09': '~でない ',
                               '*=10': '~で (~に) ',
                               '*=11': '~ですか ',
                               '*=12': '~でした',
                               '*=13': '~でする　',
                               '*=14': '~か ',
                               '*=15': '~までも ',
                               '*=16': '~もない ',
                               '*=17': '~も[ない]',
                               '*=18': '~もなく ',
                               '*=19': '~ながら ',
                               '*=20': '~ない ',
                               '*=21': '~な(~の) ',
                               '*=22': '~ならざる ',
                               '*=23': '~ならず ',
                               '*=24': '~な[る] ',
                               '*=25': '~なさい ',
                               '*=26': '~なしの ',
                               '*=27': '~なき ',
                               '*=28': '~なく ',
                               '*=29': '~に (~は) ',
                               '*=30': '~に (~で) ',
                               '*=31': '~にも ',
                               '*=32': '~的(てき)　',
                               '*=33': '~にして ',
                               '*=34': '~に[して] ',
                               '*=35': '~にない ',
                               '*=36': '~になって',
                               '*=37': '~になっている ',
                               '*=38': '~にある ',
                               '*=39': '~にさせる ',
                               '*=40': '~にいる ',
                               '*=41': '~にならない ',
                               '*=42': '~されて　',
                               '*=43': '~[に]する ',
                               '*=44': '~にやる　',
                               '*=45': '~[の]ある ',
                               '*=46': '~のした ',
                               '*=47': '~のしない ',
                               '*=48': '~のする ',
                               '*=49': '~を ',
                               '*=50': '~[を]する ',
                               '*=51': '~をしている　',
                               '*=52': '~をした ',
                               '*=53': '~をやる ',
                               '*=54': '~させる ',
                               '*=55': '~される ',
                               '*=56': '~してある ',
                               '*=57': '~す　',
                               '*=58': '~[します ',
                               '*=59': '~しない ',
                               '*=60': '~せずに ',
                               '*=61': '~せる ',
                               '*=62': '~となる ',
                               '*=63': '~とさせる ',
                               '*=65': '~[と]した ',
                               '*=66': '~と[して] ',
                               '*=67': '~[とも',
                               '*=68': '~[と]もすれば ',
                               '*=70': '~と[なく] ',
                               '*=71': '~へ ',
                               '*=72': '~されている ',
                               '*=73': '~がごとし ',
                               '*=74': '~だから　',
                               '*=75': '~だけの ',
                               '*=78': '~す[る] ',
                               '*=79': '~ならば ',
                               '*=80': '~ならぬ ',
                               '*=81': '~ならしめる ',
                               '*=82': '~に[なって]　',
                               '*=83': '~をしない ',
                               '*=84': '~をして ',
                               '*=85': '~しながら ',
                               '*=86': '~すべき ',
                               '*=87': '~すれば ',
                               '*=88': '~しても　',
                               '*=91': '~となって　',
                               '*=93': '~において '}

        asterisk_dict = {'*0': '~した ',
                         '*1': '~する ',
                         '*2': '~な ',
                         '*3': '~の ',
                         '*4': '~に ',
                         '*5': '~で ',
                         '*6': '~と ',
                         '*7': '~たる ',
                         '*8': '~して ',
                         '*9': '~している '}

        at_dict = {'@0': '_употребляется фонетически_', '@3': ' и т.д.', '@4': 'В сочетаниях непродуктивен',
                   '@6': 'в сочетаниях то же'}

        greater_than_dict = {'>1': '_мужское имя_',
                             '>2': '_женское имя_',
                             '>3': '_фамилия_',
                             '>4': '_псевдоним_',
                             '>5': '_топоним_',
                             '>11': '_мужские имена_',
                             '>12': '_мужское либо женское имя_',
                             '>13': '_мужское имя либо фамилия_',
                             '>21': '_женское либо мужское имя_',
                             '>22': '_женские имена_',
                             '>23': '_женское имя либо фамилия_',
                             '>30': '_имя либо фамилия_',
                             '>33': '_фамилии_',
                             '>35': '_фамилия и топоним_',
                             '>44': '_псевдонимы_',
                             '>50': '_имя либо топоним_',
                             '>53': '_фамилии и топонимы_',
                             '>55': '_топонимы_'}
        dicts = triple_asterisk_dict | double_asterisk_dict | asterisk_dict | asterisk_hyphen_dict |\
            asterisk_equal_dict | at_dict | greater_than_dict
        for values in dicts.items():
            meaning = meaning.replace(values[0], values[1])
        for char in '@', '=', '{', '}', '+':
            meaning = meaning.replace(char, '')

        return meaning

    def add_kanji(self, kana: str) -> tuple:
        nomers = re.findall(r"#(\d+)#", kana)
        kanjis = [chr(
            self.cur.execute(f"SELECT Uncd FROM Kanji WHERE Nomer = {kanji}").fetchone()[0]) for kanji in nomers]
        return nomers, kanjis

    def add_okurigana(self, word_nom: int) -> str:
        word = ""
        k_1, k_2, k_3, k_4, kana = self.cur.execute(
            f"SELECT K1, K2, K3, K4, Kana FROM Tango WHERE Nomer = {word_nom}").fetchone()
        kanjis = ''.join([chr(
            self.cur.execute(f"SELECT Uncd FROM Kanji WHERE Nomer = {kanji}").fetchone()[0]) for kanji in [
            k_1, k_2, k_3, k_4] if kanji != 0 and kanji != -1])
        if kanjis:
            if "#" in kana:
                nomers, extra_kanjis = self.add_kanji(kana)
                for nomer in nomers:
                    kana = kana.replace(f"#{nomer}#", '')
                else:
                    kanjis += ''.join(extra_kanjis)
            okuriganas = {int(num): Kanji.to_kana(
                okurigana) for num, okurigana in re.findall(r"(\d)([a-z^()\[\]]+)", kana)} | {
                int(num): Kanji.to_kana(
                    okurigana, is_katakana=True) for num, okurigana in re.findall(r"(\d)\^([a-z^()\[\]]+)", kana)
            }
            word = kanjis
            for num, kanji in enumerate(kanjis):
                if num + 1 in okuriganas.keys():
                    word = word.replace(kanji, kanji + okuriganas[num + 1])
                    kanjis = kanjis[:num] + kanjis[num+1:]
            if "0" in kana:
                word = okuriganas[0] + word
        elif kana:
            word = Kanji.to_kana(kana)

        return word

    def __del__(self):
        self.con.close()


if __name__ == '__main__':
    kanji_char = input('Kanji here: ')
    kanji = Kanji(kanji_char)
    print(kanji.get_info())
