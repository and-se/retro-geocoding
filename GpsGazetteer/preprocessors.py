import re
from html.parser import HTMLParser


# from text_tools.space_normalize import clear_text_line

# TODO Словарь для правки ошибок текста и патчинга, сигналы (пропатченная, непропатченная строка), EngInRusWordsTextPreprocessor
# УстьКаменогорск  [А-Я][а-я]+[А-Я]


class HtmlTextAndPatchExtractor(HTMLParser):
    """
    Парсер для извлечения частей текста и патчей к ним из html-страницы.

    Необходимо указать теги, содержимое которых расценивается как строка текста.
    Содержимое такив тегов превращается в список пар (тип, текст), где тип - TEXT или PATCH + имя тега.
    Внутри таких тегов могут быть другие теги - теги патчей, пропускаемые теги (на выходе их содержимого нет),
    игнорируемые теги (игнорируем их открытие и закрытие).
    При необходимости такой список пар можно преобразовать к более удобному виду при помощи postprocessor.
    """
    INIT_TAG = "{wait for text tag}"

    def __init__(self, text_tags='p', patch_tags="", skip_data_tags="", ignore_tags="",
                 postprocessor=lambda item: item):
        """
        Инициализация парсера
        :param text_tags: теги, содержимое которых надо расценивать как строку данных (строка через пробел)
        :param patch_tags: теги внутри text_tags, содержимое которых надо расценивать как патч к основному тексту
        :param skip_data_tags: теги внутри text_tags, содержимое которых надо пропускать
        :param ignore_tags: теги, наличие которых надо вообще игнорировать (но данные внутри читаются)
        :param postprocessor: поспроцессор извлечённой строки данных.
        """
        super().__init__()
        ignore_tags += " br img"

        self._text_tags = text_tags.split()
        self._skip_data_tags = skip_data_tags.split()
        self._patch_tags = patch_tags.split()
        self._ignore_tags = ignore_tags.split()
        self.postprocessor = postprocessor
        self.data = []

        self._cur_tag = self.INIT_TAG
        self._cur_item = []
        self._line_number = None
        self._tag_stack = []

    def process(self, filename):
        self.reset()
        with open(filename, 'r', encoding='utf8') as inf:
            for i, l in enumerate(inf):
                self._line_number = i
                self.feed(l)

        self._line_number = None
        if self._cur_tag != self.INIT_TAG:
            raise Exception(f"Expected INIT_TAG {self.INIT_TAG} at end, but got {self._cur_tag}. "
                            f"cur_item = {self._cur_item}")
        if self._cur_item:
            raise Exception(f"Some data not flushed: cur_item={self._cur_item}")

        if self._tag_stack:
            raise Exception("Tag stack isn't empty!")

    def handle_starttag(self, tag, attrs):
        if tag in self._ignore_tags:
            return
        if self._cur_tag == self.INIT_TAG:
            if tag in self._text_tags:
                self._set_cur_tag(tag)
            else:
                # self._warn(f"Skip unexpected tag {tag} while expect text tag {self._text_tags}")
                pass
        elif self._cur_tag in self._text_tags:
            if tag in self._patch_tags + self._skip_data_tags:
                self._set_cur_tag(tag)
            else:
                self._warn(f"Unexpected tag {tag} while reading text of {self._cur_tag}", throw=True)
        else:
            self._warn(f"Unexpected tag {tag} for cur tag {self._cur_tag}")

    def handle_data(self, data):
        data = data.strip()
        if not data:
            return
        if self._cur_tag in self._text_tags:
            self._append_item(f"TEXT {self._cur_tag}", data)
        elif self._cur_tag in self._patch_tags:
            self._append_item(f"PATCH {self._cur_tag}", data)
        elif self._cur_tag in self._skip_data_tags:
            pass
        else:
            self._warn(f"Skip data {data} for cur_tag={self._cur_tag} line={self._line_number}")

    def handle_endtag(self, tag):
        if tag in self._ignore_tags:
            return
        if self._cur_tag == self.INIT_TAG:
            pass
        elif self._cur_tag in self._text_tags:
            if tag in self._text_tags:
                self._push_item()
                self._restore_cur_tag(self.INIT_TAG)
            else:
                self._warn(f"Unexpected end tag {tag} while reading text from {self._cur_tag}", throw=True)
        elif self._cur_tag in self._patch_tags + self._skip_data_tags:
            if tag == self._cur_tag:
                self._restore_cur_tag(self._text_tags)
            else:
                self._warn(f"Unexpected end tag {tag} for cur tag {self._cur_tag}", throw=True)
        else:
            self._warn(f"Unexpected end tag {tag} for cur tag {self._cur_tag}", throw=True)

    def _set_cur_tag(self, tag):
        self._tag_stack.append(self._cur_tag)
        self._cur_tag = tag
        # print(f"Change cur tag from {self._cur_tag} to {tag}")

    def _restore_cur_tag(self, expected):
        tag = self._tag_stack.pop()
        if isinstance(expected, str):
            expected = [expected]

        if tag not in expected:
            raise ValueError(f"Expected tag {expected}, but got {tag}")
        self._cur_tag = tag

    def _push_item(self):
        data = self.postprocessor(self._cur_item)
        self.data.append(data)
        self._cur_item = []

    def _append_item(self, _type, text):
        if not self._cur_item:
            self._cur_item.append((_type, text))
            return
        last_type, last_text = self._cur_item[-1]
        if last_type == _type:
            self._cur_item[-1] = (_type, _append_str(last_text, text))
        else:
            self._cur_item.append((_type, text))

    def save(self, filename):
        with open(filename, 'w', encoding='utf8') as f:
            for i in self.data:
                f.write(str(i) + '\n')

    @staticmethod
    def _warn(message, throw=False):
        if throw:
            raise Exception(message)
        else:
            print(message)

    def error(self, message):
        raise Exception(message)


def resolve_patches(item, manual_patch_dict=None):
    result = ''
    manual_patch_dict = manual_patch_dict or {}
    for i in range(len(item)):
        cur_type, cur_text = item[i]
        if cur_type.startswith("TEXT"):
            # try replace text cur_text with manual
            manual = manual_patch_dict.pop(cur_text, None)
            if manual:
                cur_text = manual
            result = _append_str(result, cur_text)
        elif cur_type.startswith("PATCH"):
            old_r = result
            # try replace pair (text, patch) manual
            manual = manual_patch_dict.pop((result, cur_text), None)
            if manual:
                result, ok = manual, True
                print(f"<!> manual patch '{old_r}' to '{result}'")
            else:
                result, ok = apply_patch(result, cur_text)
            # if not ok: print(f"Skip patch {old_r} <-- {cur_text}")
        else:
            raise ValueError(f"Known types are TEXT and PATCH, but got {cur_type}")
    return result


def apply_patch(text, patch):
    word_re = r'[А-ЯЁа-яё-]+'
    if patch.strip().startswith('('):  # патч в скобках - ничего не заменяем
        return _append_str(text, patch), False

    # Считаем, сколько слов в патче. Готовы заменять не более двух
    try_two_words = len(patch.split()) == 2
    # Регулярка для поиска одного слова с конца текста
    efforts = [rf"\b{word_re}\b[.]?$"]
    if try_two_words:
        # Регулярка поиска 2 слов с конца
        efforts.insert(0, rf"\b{word_re}\b\W*\b{word_re}\b[.]?$")
    for regex in efforts:
        place_for_patch = re.search(regex, text)
        if place_for_patch:
            # Берём первые буквы патча и заменяемого слова
            mask = place_for_patch.group()[0] + patch[0]
            # Если буквы одинакового регистра - применяем патч
            if mask.islower() or mask.isupper():
                # Т.к. патче в конце текущей строки, .end() не выписываем
                result = text[:place_for_patch.start()] + patch
                return result, True

    # Не удалось применить патч - просто дописываем его после текста
    return _append_str(text, patch), False


def _append_str(s, s_plus):
    s = s.strip()
    s_plus = s_plus.strip()
    if not s:
        return s_plus
    elif not s_plus:
        return s
    else:
        space = " " if s[-1] not in "(=&" and s_plus[0] not in ")=&" else ""
        return s + space + s_plus

