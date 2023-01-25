import re

_camel_case_regex = re.compile(r'(?<!^)(?=[A-Z])')


def camel_case_to_snake_case(text):
    """
    Приводит текст из camel case в snake case
    :param text: текст в ВерблюжьемРегистре
    :return: текст в змеином_регистре
    """
    return _camel_case_regex.sub("_", text).lower()
