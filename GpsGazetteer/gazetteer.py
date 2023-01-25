import pickle
import typing
from os import path, makedirs
import sqlite3

from GpsGazetteer.common import GeoName, MapPoint, GeoNameItem
from geoparsing import geoparser
import sql_query


def build_geo_name(name: str) -> GeoName:
    try:
        parsed = geoparser.parse_string(name)
    except geoparser.GeoParserException as ex:
        raise GazetteerException(ex) from ex
    else:
        return GeoName.build_from_geoparser_dict(parsed)


class SimpleGpsGazetteer:
    def __init__(self, gps_points: typing.List[MapPoint]):
        self._data = list(gps_points)

    def find(self, name: typing.Union[GeoName, str]) -> typing.Iterable[MapPoint]:
        if isinstance(name, str):
            name = build_geo_name(name)
        elif not isinstance(name, GeoName):
            raise ValueError(f"name: expected str or GeoName")

        for p in self._data:
            if p.geo_name.matches(name):
                yield p


def de_yo(s):
    """
    Remove Ё, which may suddenly appear after pyparsing2 inflect (version/dict dependent?)
    """
    return s.replace('ё', 'е').replace('Ё', 'Е')


class SqliteGpsGazetteer:
    _search_fields = ("country", "region", "sub_region", "district", "sub_district",
                      "town", "sub_town", "place")

    _data_fields = ("lat", "long", "prob")

    def __init__(self, dbpath: str):
        if not path.exists(dbpath):
            self._init_db(dbpath)

        self._conn = sqlite3.connect(dbpath)
        self._conn.execute("pragma journal_mode=wal")
        self._conn.row_factory = sqlite3.Row

    def find(self, name: GeoName) -> typing.Iterable[MapPoint]:
        sql = sql_query.SelectQuery("Geo")

        for fld in self._search_fields:
            sql.add_select_column(fld)
            sql.add_select_column(fld + "_type")
            sql.add_order_by(fld, nulls_last=True)
        for fld in self._data_fields:
            sql.add_select_column(fld)

        if name.section_count == 1 and name.town and name.town.type == 'город':
            # search for 'г. Курск' - no other address parts
            sql.add_where('town', '=', de_yo(name.town.name))
            # search exact город, not село, деревня etc. Or without type.
            sql.add_where_expr("""(
                town_type = ? or town_type is null
            )""", 'город')
        else:
            for fld in self._search_fields:
                cond: GeoNameItem = getattr(name, fld)
                if cond:
                    sql.add_where(fld, '=', de_yo(cond.name))

        for row in self._conn.execute(*sql.build()):
            gn: GeoName = GeoName()
            for fld in self._search_fields:
                if row[fld]:
                    gn.add(fld, row[fld], row[fld + "_type"], None)
            result: MapPoint = MapPoint(gn, row['lat'], row['long'], row['prob'])
            yield result

    def add(self, point: MapPoint):
        sql = sql_query.InsertQuery("Geo")

        for field in self._search_fields:
            d: GeoNameItem = getattr(point.geo_name, field)
            if d:
                sql.add_column(field, de_yo(d.name))
                sql.add_column(field+"_type", d.type)
        for field in self._data_fields:
            sql.add_column(field, getattr(point, field))

        self._conn.execute(*sql.build())

    def commit(self):
        """
        Commit changes into db
        :return:
        """
        self._conn.commit()

    @staticmethod
    def _init_db(dbpath: str):
        sql = sql_query.CreateTableQuery("Geo")
        indx = []
        for col in SqliteGpsGazetteer._search_fields:
            sql.add_column(col, "TEXT")
            indx.append(f"CREATE INDEX {col}_idx ON Geo({col})")
            sql.add_column(col+"_type", "TEXT")
        for col in SqliteGpsGazetteer._data_fields:
            sql.add_column(col, "REAL")

        conn = sqlite3.connect(dbpath)
        script = sql.build() + ";\n\n" + ';\n'.join(indx)
        conn.executescript(script)
        conn.commit()
        conn.close()


class GazetteerException(Exception):
    pass


Geocoder = None


def init_simple():
    global Geocoder
    data_path = path.abspath(path.join(path.dirname(__file__), 'out', 'gazetteer.pkl'))
    with open(data_path, 'rb') as f:
        points = pickle.load(f)
    Geocoder = SimpleGpsGazetteer(points)


def init_sqlite():
    global Geocoder
    dir_path = path.abspath(path.join(path.dirname(__file__), 'out'))
    if not path.exists(dir_path):
        makedirs(dir_path)
        
    data_path = path.abspath(path.join(dir_path, 'gazetteer.sqlite3'))
    Geocoder = SqliteGpsGazetteer(str(data_path))


init_sqlite()

def demo():    
    s = "1"
    while s:
        s = input("Input address: ")
        try:
            geo = geoparser.parse_string(s)
        except Exception as ex:
            print("ERROR: ", ex)
        else:
            print("Parsed:", geo)
            geo1 = GeoName.build_from_geoparser_dict(geo)
            print("Search as:", geo1)
            found = False
            for p in Geocoder.find(geo1):
                found = True
                print(p)
            if not found:
                geo2 = GeoName.build_from_geoparser_dict(geo, nowadays_main=True)
                if geo2 != geo1:
                    print("Another search as:", geo2)
                    for p in Geocoder.find(geo2):
                        print(p)


if __name__ == "__main__":
    demo()
