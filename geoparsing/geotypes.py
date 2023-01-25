# from cPyparsing import *
from pyparsing import *
from functools import reduce
from pymorphy2 import MorphAnalyzer

_morph = MorphAnalyzer()

# Настроим работу с русскоязычными ключевыми словами, что 
# нужно для задания условия совпадения только со словом, а не частью слова в
# oneOf(..asKeyword=True)
Keyword.DEFAULT_KEYWORD_CHARS += srange("[А-Яа-яЁё]")


def get_word_gender(word, priority_pos=None):
    if word in ("АССР", "ССР", "АО"):
        return "femn"  # женский род. (а мужской masc)
    if word in ("округ", "починок"):
        return "masc"
    try:
        p = next(x for x in _morph.parse(word)
                 if x.tag.gender and (not priority_pos or x.tag.POS == priority_pos))
        return p.tag.gender
    except StopIteration:
        return 'neut'  # средний род


def inflect_to_case(word, case):
    """
    Приводит слово к указанному падежу.
    Среди различных вариантов разбора выбирает первый, у которого есть падеж.
    Если таковых не имеется, возвращает исходное слово.
    """
    try:
        p = next(x for x in _morph.parse(word) if x.tag.case)
        return p.inflect({case}).word
    except StopIteration:
        return word


def inflect_to_case_and_gender(word, case, gender):
    """
    Приводит слово к указанному падежу и роду. При проблемах сначала опускает род, а 
    потом и падеж (т.е. возвращает исходное слово)
    """
    try:
        p = next(x for x in _morph.parse(word) if x.tag.case and x.tag.gender)
        r = p.inflect({case, gender})
        if not r:
            r = p.inflect({case})
        return r.word
    except StopIteration:
        return word


def is_abbrev_or_sokr(word):
    word = word.strip()
    # АССР или обл.
    return word.isupper() or word.endswith(".")


class GeoType:
    """
    Тип геообъекта. Село, город, область и т.д. и т.п.
    """

    def __init__(self, name, parser_expression, norm_title_if_type_before=True):
        """
        Создание нового геообъекта.
        name - название типа в канонической форме (город, а не г., города, городе)
        parser_expression - выражение pyparsing для использования в грамматике
        norm_title_if_type_before - нормализовать ли имя в normalize,
        если тип стоит до названия:
            Например кладбища Жуковского не надо нормализовывать в Жуковское.
            С другой стороны села Пенькова надо сделать Пеньково
        """
        self.name = name
        self._parser_expression = parser_expression
        self._normalize_type_before = norm_title_if_type_before

    @staticmethod
    def from_str(s, norm_title_if_type_before=True, caseless=True, as_keyword=True):
        words = s.split()
        name = words[0]
        expr = oneOf(words, caseless=caseless, asKeyword=as_keyword)
        return GeoType(name, expr, norm_title_if_type_before)

    def get_parser_expression(self):
        """
        Возвращает выражение pyparsing для вставки условия поиска геотипа в грамматику.
        """
        return self._parser_expression

    def normalize(self, _type, title, is_type_before_title=True):
        """
        Приведение названия нас. пункта (title) и его типа (_type) к канонической форме.
        is_type_before_title - тип стоит до названия.
        Проверяет, что переданный тип соответствует текущему геотипу, а затем
        приводит название к Именительному падежу.
        Возвращает нормализованную пару (тип, имя)
        
        """
        # if not _type or not title:
        #    raise TypeError('title and _type are required both\n' +
        #                      f"title=<{title}> _type=<{_type}>")
        if not title:
            raise TypeError('title required')
        title = title.strip()

        # Если типа нет, просто приводим к именительному падежу название
        if not _type:
            return None, inflect_to_case(title, "nomn").title()

        _type = _type.strip()
        try:
            # Проверяем, относится ли переданный тип к данному геотипу
            self._parser_expression.parseString(_type, True)
        except ParseException:
            raise ValueError(f"Wrong type {_type} for geotype {self.name}")
            # Если тип не в канонической форме или эта форма аббревиатура или сокращение,
        # то нормализуем (если не отключено _normalize_type_before)
        if _type != self.name or is_abbrev_or_sokr(self.name):
            if not is_type_before_title or self._normalize_type_before:
                gender = get_word_gender(self.name, "NOUN")
                # Согласовываем по роду, чтобы была Уфимская губерния, а не Уфимский.
                title = inflect_to_case_and_gender(title, "nomn", gender)

        # Возвращаем каноническое имя геотипа и нормализованное имя с большой буквы
        return self.name, title.title()


class CompositeGeoType:
    """
    Составной геотип, включающий в себя другие.
    Можно использовать, чтобы создать геотип "населен. пункт" 
    и положить в него простые геотипы
    "деревня", "город", "село" и т.д.
    """

    def __init__(self, geotypes):
        """
        Создаёт составной геотип на основе переданного списка геотипов
        """
        self._inner_geotypes = geotypes

    def get_parser_expression(self):
        """
        Возвращает выражение pyparsing для вставки условия поиска геотипа в грамматику.
        """
        return reduce(lambda s, i:
                      s | i.get_parser_expression(),
                      self._inner_geotypes, NoMatch())

    def normalize(self, _type, title, is_type_before_title=True):
        """
        Нормализация пары (геотип, название). Ищет первый подходящий вложенный геотип
        и делегирует работу ему. Если не найдёт - падает с ValueError
        """
        for g in self._inner_geotypes:
            try:
                return g.normalize(_type, title, is_type_before_title)
            except ValueError:
                pass
        raise ValueError(f"No geotype found for title={title} type={_type}")


def build_geo_type_from_str(s, caseless=True, as_keyword=True, norm_title_if_type_before=True):
    result = []
    for x in (x for x in s.split("\n") if x and not x.isspace()):
        result.append(GeoType.from_str(x, caseless, as_keyword, norm_title_if_type_before))
    return CompositeGeoType(result)


def build_geo_type_from_dict(d, norm_title_if_type_before=True):
    result = []
    for name, exp in d.items():
        result.append(GeoType(name, exp, norm_title_if_type_before))
    return CompositeGeoType(result)


# Типы мест на карте   
# # Родился в Ивановке - предложный падеж {loct}
# # Священник Ивановки - родительный падеж {gent}
# # Служил в с. Ивановка - именительный падеж {nomn}
PlaceFull = build_geo_type_from_str("""
    долина долины долине
    заимка заимки заимке
    источник источника источнике
    кладбище кладбища
    лесничество лесничества лесничестве
    лесопункт лесопункте лесопункта
    остров острове острова
    прииск прииске прииска
    пустошь пустоши
    роща роще рощи
    церковь церкви
""",
                                    # # лесничества Ивановского --> лесничество Ивановского,
                                    # # а не лесничество Ивановское
                                    norm_title_if_type_before=False)

PlaceShort = build_geo_type_from_dict({
    "остров": Literal("о.")
}, norm_title_if_type_before=True)

Place = CompositeGeoType([PlaceFull, PlaceShort])

# Типы нас. пунктов (дер. Ивановка)

# # Сокращения, оканчивающиеся на точку, могут не быть отдельным словом
# # (asKeyword=False, [Caseless]Literal)
# # например г.Москва, а не г. Москва

# # Для обнобуквенных сокращений требуем маленькие буквы, чтобы не путать с инициалами
# # (Literal, а не CaselessLiteral, caseless=False)

# # Но если сокращение не существует как отдельное слово, то допускаем его в любом регистре
# # даже без точки, но отдельным словом (CaselessKeyword)
TownShort = build_geo_type_from_dict({
    'город': CaselessLiteral('гор.') | Literal('г.') | CaselessKeyword('г'),
    'деревня': CaselessLiteral('дер.') | Literal("д.") | CaselessKeyword('д'),
    'ж.-д. станция': CaselessLiteral('ж.-д. ст.'),
    'местечко': CaselessLiteral('мест.') | Literal('м.'),
    'погост': CaselessLiteral('пог.'),
    'поселок': CaselessLiteral('пос.'),
    'поселок/погост/починок': Literal('п.') | CaselessKeyword('п'),
    'село': Literal('с.'),
    'слобода': oneOf('слоб. сл.', caseless=True, asKeyword=False),
    'станция': CaselessLiteral('ст.'),
    'хутор': CaselessLiteral('хут.'),
},
    norm_title_if_type_before=True)

# # Не оканчивающиеся на точку сокращения просим быть отдельным словом (asKeyword=True)
TownFull = build_geo_type_from_str("""
    аул ауле аула
    выселок выселке выселка
    завод заводе завода
    местечко местечке местечка
    погост погосте погоста пог
    посад посаде посада
    поселок поселке поселка
    починок починке починка
    село селе села
    сельцо сельце сельца
    слобода слободе слободы
    спецпоселок спецпоселке спецпоселка
    станица станице станицы
    станок станке станка
    станция станции
    трудпоселок трудпоселке трудпоселка
    урочище урочища
    хутор хуторе хутора
    деревня деревне деревни
    
    
    пустынь пустыни
    слободка слободке слободки
    наслег наслеге наслега
    """, as_keyword=True, caseless=True, norm_title_if_type_before=True)

Town = CompositeGeoType([TownShort, TownFull])

# Типы подрайонов (волость, улус, сельсовет)
SubDistrict = build_geo_type_from_dict({
    "волость": Regex(r"вол(\.|ость\b|ости\b)"),
    "улус": Regex(r"улус(а|е?)\b"),
    "сельсовет": Regex(r"сельсовет(а|е)?\b"),
}, norm_title_if_type_before=True)

# Типы районов (районы, уезды)
District = build_geo_type_from_dict({
    "район": Regex(r"р-н(а|е)?\b") | Regex(r"район(а|е)?\b") | Keyword("р."),
    "уезд": Regex(r"уезд(а|е)?\b") | Regex(r"\bу\."),
    # Майкопского отд. Кубанской обл.
    "отдел": Regex(r"отд\.") | Regex(r"отдел(а|е)?\b"),
}, norm_title_if_type_before=False)

# Типы подрегионов (округ, автономная область)
SubRegion = build_geo_type_from_dict({
    "округ": Regex(r"окр(\.|уга\b|уге\b|уг\b)"),
    "автономная область": Regex(r"АО\b"),
}, norm_title_if_type_before=False)

RepublicExpr = oneOf("республика республики республике",
                     asKeyword=True, caseless=True) | CaselessLiteral("респ.")

# Типы регионов (край, область, АССР, губерния)
Region = build_geo_type_from_dict({
    "область": Regex(r"обл(\.|асть\b|асти\b|\b)") | Keyword("о."),
    "губерния": Regex(r"губ(\.|ерния\b|ернии\b|\b)"),
    "край": Regex(r"кра(й|я|е)\b"),
    "АССР": Regex(r"АССР\b"),
    "епархия": Regex(r"епархи(и|я)\b"),
    "республика": RepublicExpr
}, norm_title_if_type_before=False)

# Типы стран
Country = build_geo_type_from_dict({
    "республика": RepublicExpr,
    "ССР": Literal('ССР'),
}, norm_title_if_type_before=True)

if __name__ == "__main__":
    import unittest


    # noinspection PyPep8Naming,SpellCheckingInspection
    class Tester(unittest.TestCase):
        Type1 = GeoType("завод", oneOf("завод завода заводе"), False)
        Type2 = GeoType.from_str("село села селе", True)
        TypeComp = CompositeGeoType([Type1, Type2])
        TypeComp2 = build_geo_type_from_str("""
        завод завода заводе
        село села селе
        """, False)

        TypeComp3 = build_geo_type_from_dict({
            "завод": oneOf("завод завода заводе"),
            "село": oneOf("село села селе")
        }, False)

        def test_zavod(self):
            T = self.Type1
            exp = ("завод", "Ивановский")
            t = T.normalize("завод", "Ивановский")
            self.assertEqual(t, exp, '1')
            t = T.normalize("завод", "Ивановский", True)
            self.assertEqual(t, exp, '11')
            t = T.normalize("завода", "Ивановского", False)
            self.assertEqual(t, exp, '2')
            t = T.normalize("завода", "Ивановского", True)
            self.assertEqual(t, ("завод", "Ивановского"), '3')
            with self.assertRaises(ValueError):
                T.normalize("село", "Ивановского")

        def test_selo(self):
            T = self.Type2
            exp = ("село", "Глинное")
            t = T.normalize("село", "Глинное")
            self.assertEqual(t, exp, '1')
            t = T.normalize("села", "Глинного")
            self.assertEqual(t, exp, '2')
            t = T.normalize("селе", "Глинном", False)
            self.assertEqual(t, exp, '3')
            with self.assertRaises(ValueError):
                T.normalize("завод", "Ивановского")

        def _test_composite(self, geotype):
            T = geotype
            t = T.normalize("села", "Гусевка")
            self.assertEqual(("село", "Гусевка"), t)
            t = T.normalize("заводе", "Уфимскому")
            self.assertEqual(("завод", "Уфимскому"), t)
            with self.assertRaises(ValueError):
                T.normalize("абра", "кадабра")

        def test_composite1(self):
            self._test_composite(self.TypeComp)

        def test_composite2(self):
            self._test_composite(self.TypeComp2)

        def test_composite3(self):
            self._test_composite(self.TypeComp3)


    unittest.main()
