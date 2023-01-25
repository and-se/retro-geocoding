import os
import re
from geoparsing.geoparser import scan_string
from text_tools.rus_eng_letters_confusion import EngInRusWordsTextPreprocessor


class TestRunner:
    def __init__(self, result_folder):
        if not os.path.exists(result_folder):
            os.mkdir(result_folder)
        self._path = result_folder
        self._textprocessor = EngInRusWordsTextPreprocessor()

    def process(self, test_file):
        with open(test_file) as f, \
                _FileMgr(os.path.join(self._path, "success.txt")) as sf, \
                _FileMgr(os.path.join(self._path, "partial.txt")) as pf, \
                _FileMgr(os.path.join(self._path, "fail.txt")) as ff:
            for l in f:
                l = l.strip()
                if not l: continue
                l = self._textprocessor.process(l)
                l = re.sub(r"\s", " ", l)
                self._process_item(l, sf, pf, ff)

        print("Success: {0}\n"
              "Partial: {1}\n"
              "Fail: {2}".format(*[x.write_count for x in (sf, pf, ff)]))
        # Эксперименты по параллельной обработке ничего не дали - работает медленнее
        # однопоточной версии - видимо из-за пересылки данных между процессами.

    def _process_item(self, item, success_file, partial_file, fail_file):
        try:
            r, s, e = next(scan_string(item))

            if s == 0 and e == len(item):
                # Если строка целиком разобрана
                self._save_result(item,
                                  r and None,  # не выводим данные разбора для удобства diff
                                  success_file)
            else:
                # Строка частично разобрана
                self._save_result(item[:s] + "<" + item[s:e] + ">" + item[e:],
                                  r and None,  # не выводим данные разбора для удобства diff
                                  partial_file)
        except StopIteration as ex:
            self._save_fail(item, fail_file)

    def _save_result(self, item, result, file_obj):
        if result:
            file_obj.write("{0}\t{1}\n", item, result.asDict())
        else:
            file_obj.write("{0}\n", item)

    def _save_fail(self, item, file_obj):
        file_obj.write(item + '\n')


class _FileMgr:
    def __init__(self, path):
        self._path = path
        self.write_count = 0
        self._file = None

    def write(self, data, *args, **kwargs):
        s = data.format(*args, **kwargs)
        self.write_count += 1
        return self._file.write(s)

    def __enter__(self):
        self._file = open(self._path, mode='w', encoding='utf8')
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._file.close()
        self._file = None


t = TestRunner("out")
t.process("test_data.txt")
