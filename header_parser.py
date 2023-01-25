import re

# Чин святости
_martyr_regex = "(Священном|Преподобном|М)учени(к|ца)"
_ispovednik_regex = "(Священнои|Преподобнои|И)споведни(к|ца)"
_other_saint_regex = r"Святитель|Преподобный|Преподобная|(Святой(\s+праведный)?)|" \
                     r"Блаженная(\s+исповедница)?|Св.(\s+страстотерпица)"


class HeaderParser():
    """Парсер заголовков статей (огрызок полного кода)"""
    
    _surface_parser = re.compile(r"""
        ^( #чин святости
           ((%s)|(%s)|(%s))\s+
        )?
        [А-ЯЁ-]{2,}(\s |, | \( | $) # Имя/Фамилия подвижника большими буквами
        """ % (_martyr_regex, _ispovednik_regex, _other_saint_regex), re.VERBOSE)

        
    def maybe_parsed(self, text):
        """
        Проверяет, может ли переданный текст быть заголовком
        Может дать ложноположительный ответ
        
        """
        if self._surface_parser.match(text):
            return True
        
        return False

