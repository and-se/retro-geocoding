from geoparsing import geoparser
from geoparsing.gps_tools import find_gps_coordinates, cover_up_gps
from text_tools import text_mark

from GpsGazetteer.common import GeoName, MapPoint
from GpsGazetteer.gazetteer import SqliteGpsGazetteer
from header_parser import HeaderParser
import pickle
import typing
import glob
from os import path, makedirs
from pathlib import Path


class MapPointBuilder(object):
    def build(self, first_geo, gps_s):
        if not first_geo:
            raise ValueError("NO GEO")
        elif first_geo.start > 0:
            raise ValueError("GEO NOT AT START")

        r1 = self._build(first_geo, gps_s, nowadays_main=False)
        r2 = self._build(first_geo, gps_s, nowadays_main=True)
        return r1 + r2

    def reset(self):
        pass

    def _build(self, first_geo, gps_s, nowadays_main: bool):
        # Разбираем результат парсинга и если получаем достаточно полное указание на точку на карте,
        # генерируем точки на карте по количествую упомянутых gps координат
        geo = GeoName.build_from_geoparser_dict(first_geo.parsed, nowadays_main=nowadays_main)
        if not geo.is_complete_point():
            raise ValueError("NOT COMPLETE GEO")

        result = []
        prob = 1 / len(gps_s)
        for gps in gps_s:
            result.append(MapPoint(geo, gps.lat, gps.long, prob))
        return result


class MapPointsBuilder:
    def __init__(self):
        self._total_points = 0
        self._fail = []
        self._prev_no_gps_line = ""
        self._header_checker = HeaderParser()
        self._point_builder = MapPointBuilder()

    def build_from_file(self, filename):
        with open(filename, encoding='utf8') as f:
            for l in f:
                item = self.build_map_points(l)
                if item:
                    for i in item:
                        yield i

    def print_statistic(self):
        print(f"GPS: Total lines {self._total_points}, Fail {len(self._fail)}")

    def build_map_points(self, line):
        line = line.strip()
        # Ищем GPS.
        gps_s = find_gps_coordinates(line)
        if not gps_s:
            # Если не нашли, проверяем, не заголовок ли это
            if self._header_checker.maybe_parsed(line):
                self._point_builder.reset()
            else:
                self._prev_no_gps_line = line
            return []

        self._total_points += 1
        # Убираем GPS из текста, чтобы не мешали парсеру
        line2 = cover_up_gps(line, gps_s)
        first_geo = self.find_first_geo(line2)

        try:
            result = self._point_builder.build(first_geo, gps_s)
        except ValueError as ex:
            self._add_fail(str(ex), line, gps_s, [first_geo] if first_geo else [])
            return []
        else:
            self._prev_no_gps_line = None
            return result

    def find_first_geo(self, line):
        """
        Поиск первого гео-объекта
        :param line: где ищем
        """
        def get_geo(l):
            geo_iter = geoparser.scan_string(l)
            return next(geo_iter, None)

        line = line.strip()
        # Пока по-простому - ищем одно гео-название в начале строки - оно и есть основное.
        # Все прочие - комментарии, которые мы пока опустим
        first_geo = get_geo(line)
        # Если гео-названия не нашли, а в предыдущей не было gps - объединяем строки и ищем снова
        if not first_geo and self._prev_no_gps_line:
            line = self._prev_no_gps_line + " " + line
            first_geo = get_geo(line)
        # Если нашли не в начале строки, то проверяем, не забыли ли указать тип насел. пункта перед названием
        if first_geo and first_geo.start > 0:
            stub = "с. "
            tmp_geo = get_geo(stub + line)
            if tmp_geo.start == 0 and tmp_geo.end == first_geo.end + len(stub):
                # удаляем фиктивный тип и сохраняем
                del tmp_geo.parsed["Town"]["Type"]
                first_geo = tmp_geo
        return first_geo

    def _add_fail(self, message, line, gps_s, geo_s):
        gps_marks = ((x.start, x.end) for x in gps_s)
        geo_marks = ((x.start, x.end) for x in geo_s)
        ds = text_mark.highlight_many(line, (gps_marks, '{}'), (geo_marks, '<>'))
        self._fail.append(f"{message}\t{ds} gps={len(gps_s)} geo={len(geo_s)}")

    def save_fail(self, path):
        with open(path, 'w') as f:
            f.writelines((x + '\n' for x in self._fail))


def remove_duplicates_and_sort_map_points(map_points: typing.List[MapPoint]):
    d = {}
    for p in map_points:
        ps = d.get(p.geo_name)
        if not ps:
            ps = set()
            d[p.geo_name] = ps
        ps.add((p.lat, p.long, p.prob))

    res = []
    for geo_name in sorted(d.keys()):
        for point in d[geo_name]:
            map_point = MapPoint(geo_name, *point)
            res.append(map_point)

    return res


def build_points_from_file(filename, fail_filename):
    bld = MapPointsBuilder()
    map_points = list(bld.build_from_file(filename))

    if fail_filename:
        bld.save_fail(fail_filename)
    bld.print_statistic()

    print("Point count", len(map_points))
    return map_points


def build_points_main():
    inputs = sorted(glob.glob("input/preprocessed/*.txt"))
    print("Files to process:", inputs)
    
    if not path.exists("out"):
        makedirs("out")

    geocoder_data = []
    for f in inputs:
        print("process", f)
        filename = path.splitext(path.basename(f))[0]
        fail_path = path.join("out", "build_fails_" + filename + ".txt")
        points = build_points_from_file(f, fail_path)
        geocoder_data.extend(points)
        print("\n\n")

    print("=============================\n")
    print("Total points", len(geocoder_data))
    geocoder_data = remove_duplicates_and_sort_map_points(geocoder_data)
    print("After removing duplicates", len(geocoder_data))

    '''with open('out/gazetteer.pkl', 'rb') as f:
        points = pickle.load(f)'''

    '''for p in points:
        print(p)'''

    res = 'out/gazetteer.pkl'
    with open(res, 'wb') as f:
        pickle.dump(geocoder_data, f)

    return res


def convert_to_sqlite(file_pkl):
    with open(file_pkl, 'rb') as f:
        points: typing.List[MapPoint] = pickle.load(f)
    db_path: Path = Path(file_pkl).with_suffix(".sqlite3")
    if db_path.exists():
        db_path.unlink()
    sqlite_g = SqliteGpsGazetteer(str(db_path))

    print("Save to db", db_path)
    print("Total points", len(points))

    for p in points:
        sqlite_g.add(p)
    sqlite_g.commit()

    print("Done")


if __name__ == "__main__":
    p = build_points_main()
    convert_to_sqlite(p)
