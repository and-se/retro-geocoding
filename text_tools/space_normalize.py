import re


def remove_bom(text):
    """
    Удаляет BOM (Byte order mark) из строки
    :param text: строка
    :return: строка без BOM
    """
    return text.replace(chr(65279), "")


def clear_text_line(text, normalize_spaces=False, remove_hyphens=True):
    """
    Очищает строку текста от нестандартных пробелов - вместо них ставит обычные.
    Обрезает начальные и конечные пробелы. Удаляет BOM.

    normalize_spaces - заменить подряд идущие пробельные символы одним
    NB! при этом потеряются табуляции и неразрывные пробелы.

    remove_hyphens - удалить символ переноса soft hyphen \u00AD,
    который визуально появляется только при необходимости разбить слово на две строки.

    """
    # Все пробельные символы заменяем на пробел
    text = re.sub(r"\s", " ", text)
    # Убираем BOM
    text = remove_bom(text)
    # Обрезаем начальные и конечные пробелы
    text = text.strip()
    if normalize_spaces:
        text = " ".join(text.split())

    if remove_hyphens:
        text = text.replace('\u00AD', "")

    return text
