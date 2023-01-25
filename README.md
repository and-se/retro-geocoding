# retro-geocoding
Наработки по ретроспективному геокодированию.

# Зависимости
* pymorphy2
* pyparsing - пока положил в репозиторий нужную версию, т.к. на актуальной версии не работает.

# Начало работы
Выполните команду `source set-env.sh` - она настроит окружение _в текущем окне консоли_.

После этого можно потестировать парсер адресов командой `python3 geoparsing/geoparser.py`.

Протестировать геокодер (т.е. поиск по адресам) можно командой `python3 GpsGazetteer/gazetteer.py`, но при первом запуске надо сначала построить БД геокодера.


# Построение БД геокодера

1. Выполнить `source set-env.sh` если ещё не делали
1. `cd GpzGazetteer` - все работы выполняем в контексте этого каталога
1. `python3 preprocess_data.py` - конвертируем html-файлы с данными в текстовые, схлопывая в итоговый текст зачёрквивания и добавки из html.
1. `python3 build_gazetteer.py` - строим БД геокодера на основе текстовых файлов

Далее можно интерактивно искать адреса в БД геокодера при помощи `python3 gazetteer.py`.


# Обзор
* `geoparsing` - парсер адресов. Знает про губернии, уезды, волости, улус, ССР и др.
    * `geoparser.py` собственно парсер. Запустите этот скрипт для интерактивного взаимодействия с парсером.
* `pyparsing.py` - сторонняя библиотека для построения грамматик. Какая-то старая версия, т.к. на современной версии что-то не работает (но это должно быть нетрудно починить). Используется в `geoparsing`.
* `GpsGazetteer` - средство для построения БД геокодера на основе имеющихся файлов с адресами и координатами
    * `input` - исходные html файлы, из которых берём адреса и координаты
    * `preprocess_data.py`, `build_gazetteer.py` - построение БД геокодера на основе html файлов с исходными данными.
    * `out` - БД геокодера (sqlite) и отчёты об ошибках при построении
    * `gazetteer.py` - собственно геокодер. Запустите этот скрипт для поиска адресов на основе ввода.
* `sql_query.py` - объектная модель SQL-запроса. Используется для взаимодействия геокодера с БД sqlite.
* `header_parser.py` - средства для обнаружения заголовков биографий (ФИО с доп. информацией). Используются при обработке входных файлов для геокодера.
* `text_tools` - утилиты для работы с текстом


# TODO
* Кажется, не стоит всегда выкидывать зачёркнутые в исходных файлах варианты адресов.
* научиться обрабатывать другие типы входных html
* Ускорить работу парсера адресов - сейчас он явно перебирает все варианты последовательностей компонент адресов (страна -- область -- район -- село; область -- район -- село; село -- район -- область и т.д.). Возможно, быстрее будет, если парсер будет только извлекать последовательность компонентов адресов, а проверять корректность последовательности будет отдельный код.
* что-то ещё...

