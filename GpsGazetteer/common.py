from collections import namedtuple

from text_tools.text_transform import camel_case_to_snake_case

GeoNameItem = namedtuple("GeoNameItem", ['name', 'type', 'parsed'])


class GeoName(object):
    """
    Гео-название (страна, регион, ... , район, ... населённый пункт, ...)
    """

    __slots__ = ("country", "region", "sub_region", "district", "sub_district",
                 "town", "sub_town", "place")

    def __init__(self):
        for field in self.__slots__:
            setattr(self, field, None)

    @staticmethod
    def build_from_geoparser_dict(parsed, nowadays_main=False):
        """
        Строит гео-название на основе результата работы геопарсера (geoparsing.geoparser.parse_string)
        """
        geo = GeoName()
        nowadays = []
        for section, data in parsed.items():
            # Ленинград, ныне С.Петербург
            if section == 'Nowadays':
                nowadays.append(data)
                continue
            # Ленинград (ныне С.Петербург)
            if "Nowadays" in data:
                nowadays.append(data["Nowadays"])
            geo.add(camel_case_to_snake_case(section), data["Name"], data.get("Type"), data)

        for n in nowadays:
            for section, data in n.items():
                geo.add(camel_case_to_snake_case(section), data["Name"], data.get("Type"), data,
                        overwrite=nowadays_main)

        return geo

    def add(self, section, name, _type, source, overwrite=True):
        if not overwrite and getattr(self, section, None):
            return
        setattr(self, section, GeoNameItem(name, _type, source))

    def is_complete_point(self):
        """Проверяет, задают ли текущие данные точку на карте"""
        if ((self.region or self.country or self.district) and (self.town or self.place)) or \
                (self.town and self.town.type == "город"):
            return True
        else:
            return False

    def matches(self, query: 'GeoName'):
        equals = []
        for section_name in self.__slots__:
            this_data = getattr(self, section_name)
            other_data = getattr(query, section_name)

            if this_data and other_data:
                if this_data.name == other_data.name:
                    equals.append(section_name)
                else:
                    return False
        return equals

    @property
    def section_count(self):
        return sum(1 if getattr(self, x) else 0 for x in self.__slots__)

    @property
    def key_section(self):
        """
        most specific address part
        """
        for section in reversed(self.__slots__):
            if getattr(self, section):
                return section

    @property
    def key_section_value(self):
        key_section = self.key_section
        if key_section:
            return getattr(self, key_section)

    def __str__(self):
        result = []
        for num, s in enumerate(self.__slots__):
            d = getattr(self, s)
            if d:
                if num < 5:
                    result.append(d.name + " " + (d.type if d.type else ''))
                else:
                    result.append(((d.type + " ") if d.type else '') + d.name)

        return ", ".join(result)

    def __repr__(self):
        return f"GeoName( {str(self)} )"

    def __eq__(self, other):
        if isinstance(other, GeoName):
            for field in self.__slots__:
                if getattr(self, field) != getattr(other, field):
                    return False
            return True
        return False

    def to_tuple(self) -> tuple:
        it = map(lambda x: (x.name, x.type or '') if x else (), (getattr(self, attr) for attr in self.__slots__))
        return tuple(it)

    def __hash__(self):
        return hash(self.to_tuple())

    def __lt__(self, other):
        if isinstance(other, GeoName):
            return self.to_tuple() < other.to_tuple()
        raise NotImplementedError()


class MapPoint:
    """Точка на карте - гео-название + GPS координаты"""

    __slots__ = ('lat', 'long', 'geo_name', 'prob')

    def __init__(self, geo_name: GeoName, lat: float, long: float, prob: float = None):
        self.geo_name = geo_name
        if not lat or not long:
            raise ValueError("GPS must contain lat and long together")
        self.lat = lat
        self.long = long
        self.prob = prob

    def __str__(self):
        return f"{str(self.geo_name)} GPS lat={self.lat} long={self.long}" + \
               (f" prob={self.prob}" if self.prob else "")

    def __repr__(self):
        return f"MapPoint( {str(self)} )"

    def __eq__(self, other):
        if isinstance(other, MapPoint):
            return self.__dict__ == other.__dict__
        return False
