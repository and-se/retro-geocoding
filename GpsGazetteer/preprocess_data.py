from text_tools.rus_eng_letters_confusion import EngInRusWordsTextPreprocessor
from GpsGazetteer.preprocessors import HtmlTextAndPatchExtractor, resolve_patches
import glob
from os import path, makedirs

# _input = 'input/sample.html'
# output = 'input/preprocessed/sample.txt'


manual_patch = {
    ('с. Святогорье Глазовского уезда', 'Вятской губ.'): 'с. Святогорье Глазовского уезда Вятской губ.',
    ('станица Александровская', 'слобода Александровская(Воронцовка)'):
        'слобода Александровская (Воронцовка) ',
    ('с.Поделец (Подоляк?)', 'Подолец'): 'с. Поделец',
    ('с. Пансуево (?)', 'Попсуево'): 'с. Попсуево',
    'Владимирской обл. (ныне ГусьХрустальный р-н) N55,428591° E40,324533°':
        'Владимирской обл. (ныне Гусь-Хрустальный р-н) N55,428591° E40,324533°'

}

# для составления словаря manual_patch полезно в sqlite-версии геокодера сделать запрос
# select * from Geo where town_type is null and town is not null
# и посмотреть те записи, у которых есть sub_town.

# Перед запуском этого скрипта желательно сделать копию папки preprocessed и сравнивать что изменилось в meld


def preprocess_data(_input, output):
    text_conv = EngInRusWordsTextPreprocessor()

    def item_processor(item):
        result = resolve_patches(item, manual_patch)
        result = text_conv.process(result)
        return result

    processor = HtmlTextAndPatchExtractor(text_tags='p h1', patch_tags='i', skip_data_tags='strike',
                                          ignore_tags='b span u a font', postprocessor=item_processor)
    processor.process(_input)
    processor.save(output)


inputs = sorted(glob.glob("input/*.html"))

prepr_path = "input/preprocessed"

if not path.exists(prepr_path):
        makedirs(prepr_path)

outputs = [path.join(prepr_path, path.basename(path.splitext(x)[0]) + ".txt") for x in inputs]

print(inputs)
print(outputs)

for inp, output in zip(inputs, outputs):
    print("Preprocess", inp, "to", output, "\n")
    preprocess_data(inp, output)
    print("\n===============\n")
    if manual_patch:
        print("WARNING - unused manual patches:", manual_patch)
