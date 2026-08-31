from json import dump, load
from .type_util import PYDict


def dict_to_json(file: str, data: PYDict, indent: int | None = None) -> None:
    """Convert python dict to json object.
    
    :param file: File path of file to save to.
    :type file: str
    :param data: Dict of data to convert.
    :type data: dict[str, Any]
    :param indent: How many spaces to indent json object. (None = no indent.)
    :type indent: int | None"""
    with open(file, 'w') as f:
        if indent:
            dump(data, f, indent=indent)
        else:
            dump(data, f)


def json_to_dict(file: str) -> PYDict:
    """Convert json object to python dict.
    
    :param file: File path to load from.
    :type file: str
    :return: Dict of converted json object
    :rtype: dict[str, Any]"""
    with open(file, 'r') as f:
        data = load(f)
    return data

