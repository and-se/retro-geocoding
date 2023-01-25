from os import path
from collections import namedtuple

from geoparsing.parsing_ext import *
from geoparsing import geotypes

_resources = path.join(path.dirname(__file__), 'resources')

# ParserElement.enablePackrat()

# Падежи, в которых могут быть названия - родительный и предложный
inflects = [{'gent'}, {'loct'}]

# Название (одно слово названия)
Title = Word(srange("[А-ЯЁ]"), srange("[а-яё]"), min=2)
# Ростов-на-Дону, Центрально-Чернозёмная обл.
Title += Optional("-" + oneOf("на в")) + Optional("-" + Title)  # двусоставное слово
Title = Combine(Title)
# сокращение Большой, Санкт, Малый, Новый, Великий и т.д.
# включаем в ближайшее слово, дабы сократить грамматику
Title = Optional(oneOf(['С.-', 'В.', 'Б.', 'М.', 'Н.'])) + Title
# 2-й Покровский Починок
Title = Optional(Regex(r"\b[0-9]+-(й|м)\b")) + Title
Title = originalTextFor(Title)


# Parse actions

def _is_type_before_title_setter(x):
    """
    Устанавливает флаг, что тип геообъекта написан до его названия
    Например, погост Ивановский, а не Ивановский погост
    """
    if x.Type:
        x['isTypeBeforeTitle'] = True


def _normalize_action(geotype):
    """
    На основе геотипа строит действие нормализации названия и типа
    """

    # на тестах к 39 секундам добавляет 20 секунд... Вот так можно временно ускорить)
    # return lambda x: None
    def normalizer(x):
        # Почему-то x.Type не запоминает...
        t, n = geotype.normalize(x.Type, x.Name, x.isTypeAfterName)
        x['Name'] = n
        if t:
            x['Type'] = t

    return normalizer


# Типы мест на карте
PlaceType = geotypes.Place.get_parser_expression()("Type")

# Типы нас. пунктов (дер. Ивановка)
TownType = geotypes.Town.get_parser_expression()("Type")

# # Типы населённых пунктов после названия, например "Никольская слобода"
TownTypeAfter = geotypes.TownFull.get_parser_expression()("Type") | \
                oneOf("слоб. хут.", caseless=True, asKeyword=False)

# Типы подрайонов (волость, улус, сельсовет)
SubDistrictType = geotypes.SubDistrict.get_parser_expression()("Type")

# Типы районов (районы, уезды)
DistrictType = geotypes.District.get_parser_expression()("Type")

# Типы подрегионов (округ, автономная область)
SubRegionType = geotypes.SubRegion.get_parser_expression()("Type")

# Типы регионов (край, область, АССР, губерния)
RegionType = geotypes.Region.get_parser_expression()("Type")

# Типы стран
CountryType = geotypes.Country.get_parser_expression()("Type")

NotTownTypes = SubDistrictType | DistrictType | SubRegionType | RegionType | CountryType
AllTypes = NotTownTypes | TownType

InBrackets = Forward()

# Скобки между названием и типом - Ивановской (Петровской) обл - понимаем примерно также
NameBrackets = Forward()

# Место
Place = PlaceType + originalTextFor(
    Title + Optional(Title + ~FollowedBy(TownType | NotTownTypes)))("Name")
Place.setParseAction(_is_type_before_title_setter)

PlaceAfter = originalTextFor(Title + Optional(Title + FollowedBy(PlaceType)))("Name") + \
             PlaceType + ~FollowedBy(Title * 2)
Place |= PlaceAfter

Place += InBrackets
Place.setParseAction(_normalize_action(geotypes.Place))
Place = Group(Place)("Place")

# Населённый пункт
Town = TownType + originalTextFor(
    Title + Optional(Title + ~FollowedBy(Optional(NameBrackets) + AllTypes))   # ~FollowedBy(Optional(NameBrackets) + AllTypes)
)("Name") + Optional(NameBrackets + FollowedBy("("))
Town.setParseAction(_is_type_before_title_setter)

# Отсеиваем совпадение <Иван слободы> Ивановской Сельского уезда
TownAfter = originalTextFor(Title)("Name") + Optional(NameBrackets) + TownTypeAfter + ~FollowedBy(Title * 2)
TownAfter |= originalTextFor(Title + Optional(Title))("Name") + TownTypeAfter + ~FollowedBy(Title * 2)

Town |= TownAfter
Town |= one_of_file(path.join(_resources, 'towns.txt'), inflects)("Name")
Town |= originalTextFor(Title)("Name") + FollowedBy(Suppress(Title + AllTypes))
Town += InBrackets
# Town = Town + Optional(Group("(" + Town + ")")("Other"))
Town.setParseAction(_normalize_action(geotypes.Town))
Town = Group(Town)("Town")

# Подрайон (волость, сельсовет)
SubDistrict = Title("Name") + Optional(NameBrackets) + SubDistrictType
SubDistrict += InBrackets
SubDistrict.setParseAction(_normalize_action(geotypes.SubDistrict))
SubDistrict = Group(SubDistrict)("SubDistrict")

# Район
District = Title("Name") + Optional(NameBrackets) + DistrictType
District += InBrackets
District.setParseAction(_normalize_action(geotypes.District))
District = Group(District)("District")

# Подрегион (округ, АО)
SubRegion = Title("Name") + Optional(NameBrackets) + SubRegionType
SubRegion += InBrackets
SubRegion.setParseAction(_normalize_action(geotypes.SubRegion))
SubRegion = Group(SubRegion)("SubRegion")

# Регион (область, губерния, край, епархия)
Region = Title("Name") + Optional(NameBrackets) + RegionType
RegionDict = Optional(geotypes.RepublicExpr)("Type") + \
             one_of_file(path.join(_resources, 'regions.txt'), inflects)("Name")
RegionDict.setParseAction(_is_type_before_title_setter)

Region |= RegionDict
Region += InBrackets
Region.setParseAction(_normalize_action(geotypes.Region))
Region = Group(Region)("Region")

# # Маленькое дополнение
# # Амурской обл. Дальневосточного края - в данном случае обл. это SubRegion, а не Region
_SubRegionTune = Title("Name") + Regex(r"обл(\.)?")("Type") + InBrackets
_SubRegionTune.setParseAction(_normalize_action(geotypes.Region))

_SubRegionTune = Group(_SubRegionTune)("SubRegion") \
                 + FollowedBy(Region)

SubRegion |= _SubRegionTune

# Условно страны, но может входить и в состав бОльшей страны, например ССР в СССР
Country = Title("Name") + Optional(NameBrackets) + CountryType("Type")
CountryDict = Optional(geotypes.RepublicExpr)("Type") + \
              one_of_file(path.join(_resources, 'countries.txt'), inflects)("Name")
CountryDict.setParseAction(_is_type_before_title_setter)

Country |= CountryDict
Country |= (geotypes.RepublicExpr("Type") + Title("Name")).setParseAction(_is_type_before_title_setter)
Country += InBrackets
Country.setParseAction(_normalize_action(geotypes.Country))
Country = Group(Country)("Country")

# Главная часть названия

# # Prefix
preposition = oneOf("в при близ у под", asKeyword=True).suppress()
Prefix = Place + Optional(preposition | ",")
# # Дорого! + 5 сек. на тестах
Prefix |= Town("SubTown") + Optional(preposition) + FollowedBy(Town)

# Прямой разбор - г. Видное Московской области России
MainGeo = all_sub_chains(Town, SubDistrict, District, SubRegion, Region, Country,
                         delimeter=Optional("," | Regex(r"\bв\b")),
                         # item_tail = EndMark
                         )
MainGeo = Optional(Prefix) + MainGeo

# Разбор наоборот:  Россия, Московская область, г. Видное
# NB! Сильно просаживает производительность... Возможно, надо
# попробовать объединить два вызова all_sub_chains и избавистья от ^
# (поиск наиболее длинного совпадения) в пользу | (поиск первого совпадения)
MainGeo ^= all_sub_chains(Country, Region, SubRegion, District, SubDistrict, Town,
                          delimeter=Optional(",")
                          )

# Сведения о том, где искать сейчас
NowadaysInBrackets = Suppress("(" + Optional("ныне")) + MainGeo + Suppress(Regex(r"\)|$"))  # ) могут и забыть
NowadaysInBrackets = Group(NowadaysInBrackets)("Nowadays")

NowadaysAfterComma = Suppress(Literal(",") + "ныне") + MainGeo
NowadaysAfterComma = Group(NowadaysAfterComma)("Nowadays")

# # #Nowadays = NowadaysInBrackets | NowadaysAfterComma

# Комментарий для всего того, что разобрать не удалось
Comment = Suppress("(") + Regex(r"[^)]+") + Suppress(Regex(r"\)|$"))  # закрывающую ')' могут и забыть
Comment = ungroup(Comment)("Comment")

# Расскажем наконец, как понимать выражения в скобках
InBrackets << Optional(NowadaysInBrackets | Comment)
# InBrackets << Empty()

OtherName = Suppress("(" + Optional("ныне")) + Title("Name") \
            .setParseAction(lambda x: geotypes.inflect_to_case(x[1], 'nomn').title()) + \
            Suppress(Regex(r"\)|$"))

NameBrackets << Group(ungroup(NowadaysInBrackets) | OtherName | Comment)("NameBrackets")

# Парсер географии строка
# Слова в скобках будут прикреплены к последней компоненте адреса.
# И только "ныне" после запятой - к самому адресу...
Geo = MainGeo + Optional(NowadaysAfterComma)

# \b - чтобы не поймать "и вот ито<г. Москва>, 2020.
Geo = Regex(r"\b") + Geo + Optional(".")  # + EndMark


def parse_string(s: str, whole_string=True):
    """
    Разбирает строку с географическим названием на компоненты
    :param s: строка для разбора
    :param whole_string: нужно разбирать всю строку либо можно остановиться в середине, если что-то пойдёт не так?
    :return: словарь с результатами разбора
    Основные ключи словаря (хотя бы один из них обязательно будет):
        Town - населённый пункт (город, деревня, село ...)
        SubDistrict - подрайон (волость, улус, сельсовет)
        District - район (уезд)
        SubRegion - подрегион (округ, автономная область)
        Region - регион (край, область, АССР, губерния)
        Country - условно страна (Франция, руспублика, ССР)
    Дополнительные ключи словаря:
        Place - место (<Долина Псху> близ хутора Ригза, кладбище, церковь ...)
        SubTown - насел. пункт внутри другого (<Хутор Зимняцкий> Глазуновской станицы)

    В каждом элементе словаря лежит подсловарь с ключами:
        Name - название (обязательный)
        Type - тип (город, район, область ...) - если есть в исходном тексте
        isTypeBeforeTitle = True - если Type в тексте стоит до Title (г. Москва, но не Уфимская губ.)

    Если в разбираемой строке есть уточнения в скобках *после* какого-либо компонента даты,
    то кроме Title и Type к компоненте адреса добавляется один из двух ключей:
        Nowadays - разобранное как гео-адрес содержимое скобок (г. Романов-Борисоглебск (<ныне г.Тутаев>))
        Comment - текст из скобок, если его не удалось разобрать
    Например, это случится для Ивановская область (ныне Рязанская область).

    Если скобки стоят внутри компонента даты - между именем и типом, то добавляется ключ NameBrackets,
    внутри которого либо результат разбора вложенного адреса, либо ключ Name с другим именем, либо ключ Comment.
    Например, это случится для Ивановская (ныне Рязанская) область.

    Nowadays также добавляется к списку ключей верхнего уровня в случае ", ныне":
        г.Романов-Борисоглебск, <Nowadays>ныне г.Тутаев</>
    """
    try:
        result = Geo.parseString(s, whole_string).asDict()
    except Exception as ex:
        raise GeoParserException(ex) from ex
    else:
        return result


GeoTextEntity = namedtuple('GeoTextEntity', ['parsed', 'start', 'end'])
"""Гео-название в тексте - кортеж (результат разбора, позиция начала, позиция окончания)"""


def scan_string(s: str) -> GeoTextEntity:
    """
    Производит поиск непересекающихся гео-адресов в строке
    :param s: строка, в которой ищем адреса
    :return: итератор, элементами которого является кортеж GeoTextEntity, моделирующий тройку
    (разобранный адрес, позиция начала гео-адреса, позиция окончания)

    Описание формата разобранного адреса см. в parse_string.
    """
    for p, s, e in Geo.scanString(s, overlap=False):
        yield GeoTextEntity(p.asDict(), s, e)


class GeoParserException(Exception):
    """
    Ошибка при парсинге адреса
    """
    pass


def set_debug_names():
    """
    Устанавливает читаемые имена всем ParserElement, которые лежат в памяти... ОПАСНО!
    """
    for key, var in globals().items():
        if isinstance(var, ParserElement):
            var.setName(key)


def interactive_ui():
    """
    Очень простой UI для тестирования геопарсера
    """
    while True:
        s = input("Введите место: ")
        if not s: return

        try:
            print(parse_string(s, False))
        except Exception as ex:
            print(ex)


if __name__ == "__main__":
    import sys

    if 'test' in sys.argv:
        verb = 'verbose' in sys.argv
        from geoparsing.parser_tests import tests_ui

        tests_ui(verb)
    else:
        set_debug_names()
        interactive_ui()
