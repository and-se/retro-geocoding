# from cPyparsing import * # Не сильно быстрее
from pyparsing import *
from pymorphy2 import MorphAnalyzer

morph = None

def one_of_file(path, inflects=None):
    """
    Условие совпадения с одной из строк файла.
    inflects = помимо исходной строки нужно сравнивать со склонениями в указанные морфологические формы
    """
    dd = []
    with open(path) as f:
        for l in f:
            l = l.strip()
            if not l: continue
            dd.append(l)     
            for i in do_inflects(l, inflects):
                dd.append(i)

    # print(dd)
    
    # Ищем слово из списка, обрамлённое границей слов \b
    # (\b - граница между словным (\w) и несловным (\W) символом или границей строки (^$) )
    # Используем Combine, чтобы не пропускались пробелы, иначе границы будут искаться не там.
    result = Combine(Regex("\\b") + oneOf(dd) + Regex("\\b"))
    #result = oneOf(dd)
    result = ungroup(result)
    return result


def all_sub_chains(*components, delimeter = Empty(), item_tail = Empty()):
    """
    По переданной цепочке pyparsing-выражений строит все подцепочки, в которых
    обязательно только первое выражение.
    Параметр delimeter позволяет задать разделитель между элементами цепочки
    Параметр item_tail - выражение после каждого элемента цепочки.
    
    Например, all_sub_chains(A, B, C) выдаст:
    A + Optional(B) + Optional(C) |
    B + Optional(C) |
    C
    """
    components = list(components)
    chains = []
    while components:
        chain = components[0] + item_tail
        for x in components[1:]:
            chain += Optional(delimeter + x + item_tail)
        chains.append(chain)
        del components[0]
        
    result = chains[0]
    for ch in chains[1:]:
        result |= ch
    
    return result
    
def _morph():
    global morph
    if not morph:
        morph = MorphAnalyzer()
    return morph

def do_inflects(word, inflects):
    """
    Склонение слова word в несколько разных форм.
    Если в word словосочетание, то склоняется каждое слово словосочетания.
    Возвращает список результатов.
    """
    if not inflects:
        return [word]
    
    def inflecter(w):
        is_title, is_upper = w.istitle(), w.isupper()        
        w = _morph().parse(w)[0]
        # inflect or w - если не удалось склоненине, берём изначальное слово
        result = [(w.inflect(x) or w).word for x in inflects]
        if is_title:
            result = [x.title() for x in result]
        elif is_upper:
            result = [x.upper() for x in result]
        return result
    
    words = word.split()        
    # Для каждого слова получаем список склонений
    result = map(inflecter, words)
    # Объединяем списки поэлементно, так что получится список
    # кортежей (слово1, слово2, ....)
    result = zip(*result)        
    # Превращаем кортежи в словосочетания
    result = map(" ".join, result)
    
    return list(result)

    
if __name__ == "__main__":
    d = do_inflects("Иван Иванович МГУ", [{'nomn'}, {'gent'}])
    print(d)
    
    d = do_inflects("Ух Иванович малый", [{'nomn'}, {'gent'}])
    print(d)
    
