import re
from collections import namedtuple
from typing import List

GpsTextEntity = namedtuple("GpsTextEntity", ['start', 'end', 'lat', 'long'])
"""GPS координаты в тексте - кортеж <начало, конец, широта, долгота>"""


def find_gps_coordinates(line) -> List[GpsTextEntity]:
    """
    Ищет GPS-координаты в тексте
    :param line: текст
    :return: список найденных координат в виде кортежей GpsTextEntity
    """
    re_gps = r''',?\s*
               (
                    N|(lat\s*=?\s*)
               )?\s*
               
               (?P<lat>\d+[.,]\d+)
               \s* (°|º)? \s*
               
               (&|,)?
               \s*
               
               (    E|Е # англ. и русская Е
                    | (long\s*=?\s*)
               )?\s*
               
               (?P<long>\d+[.,]\d+)
               (°|º|
               (&name=[^ ]\b)
               )?
               '''

    def numb(s):
        return float(s.replace(",", "."))

    result = []
    for l in re.finditer(re_gps, line, re.X):
        result.append(
            GpsTextEntity(l.start(), l.end(), numb(l.group("lat")), numb(l.group("long")))
        )

    return result


def cover_up_gps(line: str, gps_s: List[GpsTextEntity]) -> str:
    """
    Замазывает gps-координаты в тексте: заменяет на ")" + необходимое количество пробелов,
    чтобы размер строки не изменился.
    """
    result = ""
    i = 0

    for s, e, _, _ in gps_s:
        result += line[i:s] + ")" + " " * ((e - s)-1)
        i = e
    result += line[i:]

    return result
