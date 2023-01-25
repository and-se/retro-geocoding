import sys
from os.path import abspath, split, join

cur_dir = split(abspath(__file__))[0]
sys.path.append(abspath(join(cur_dir, "..", "..")))


from argparse import ArgumentParser

parser = ArgumentParser(description="Интерфейс командной строки к пакету средств работы с текстом text_tools")

parser.add_argument("text", help="Входной текствый файл. Для ввода с клавиатуры введите *stdin*")
parser.add_argument("-o", "--output-text", help="Выходной текстовый файл - по умолчанию <text>_processed.<ext>."
                                                "Для вывода на экран введите *stdout*")

parser.add_argument("--remove-BOM", action="store_false", help="Удалить BOM из текста")
parser.add_argument("--replace-eng-to-rus", choices=['in-words', 'all'],
                    help='''Заменять английские буквы на русские:
* in-words - в словах, где есть русские буквы
* all - в словах, где есть русские буквы, а также в одиночных словах NB! может ломать гиперссылки!''')

from text_tools.space_normalize import remove_bom
from text_tools.rus_eng_letters_confusion import EngInRusWordsTextPreprocessor

args = parser.parse_args()

if args.text == '*stdin*':
    result = input("Введите текст: ")
    if not args.output_text:
        args.output_text = "*stdout*"
else:
    with open(args.text) as f:
        result = f.read()

if args.remove_BOM:
    result = remove_bom(result)

if args.replace_eng_to_rus:
    replace_single = args.replace_eng_to_rus == 'all'
    p = EngInRusWordsTextPreprocessor()
    result = p.process(result, replace_single)

if args.output_text == "*stdout*":
    print(result)
else:
    if not args.output_text:
        from os import path
        file, ext = path.splitext(args.text)
        args.output_text = file + "_processed" + ext

    print("Saving to ", args.output_text)
    with open(args.output_text, 'w') as f:
        f.write(result)
