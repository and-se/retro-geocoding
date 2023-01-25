import typing


def highlight(text: str, intervals: typing.Iterable[typing.Tuple[int, int]], marks=("<", ">")):
    """
    Выделение ("подсветка") элементов текста

    :param text: исходный текст
    :param intervals: список пар индексов символов (от, до), которые надо подсветить
    :param marks: пара меток - для окончания и для начала подсветки
    :return: строка, в которой на концах заданных интервалов расставлены метки.
    """
    return highlight_many(text, (intervals, marks))


def highlight_many(text: str, *intervals_frame_pairs):
    """
    Выделение ("подсветка") элементов текста разными способами.

    :param text: исходный текст
    :param intervals_frame_pairs: пары (интервалы, метки), где:
    * интервалы - список интервалов номеров символов (от, до)
    * метки - пара (метка начала выделения, метка конца выделения), в простейшем случае строка из двух символов

    :return: строка, в которой в указанных местах расставлены заданные метки.
    """
    # Даны пары (где_ставить_метки, (метка начала, метка конца))
    marks = []
    for intervals, frames in intervals_frame_pairs:
        marks += build_pos_mark_list(intervals, frames[0], frames[1])
    marks = sorted(marks, key=lambda x: x[0])
    i = 0
    r = ""
    for pos, symbol in marks:
        r += text[i:pos] + symbol
        i = pos

    r += text[i:]
    return r


def build_pos_mark_list(intervals, left_bracket, right_bracket):
    """
    По списку интервалов и меток начала и конца выделения формирует упорядоченный по номеру символа список
    мест, куда надо вставить метку.
    :param intervals: интервалы для выделения -список пар (от, до)
    :param left_bracket: метка начала выделения
    :param right_bracket: метка окончания выделения
    :return: список пар (номер символа, метка), упорядоченный по номеру символа
    """
    marks = []
    for s, e in intervals:
        # конвертируем в множество пар (позиция, метка)
        marks.append((s, left_bracket))
        marks.append((e, right_bracket))

    # сортируем в порядке возрастания номеров символов
    marks = sorted(marks, key=lambda x: x[0])
    return marks


if __name__ == "__main__":
    print(highlight_many("У Лукоморья дуб зелёный!",
                         ([(12, 15)], ("{=", "=}")),
                         ([(2, 11)], "<>")
                         ))

    print(highlight("У Лукоморья дуб зелёный", [(2, 11)]))
