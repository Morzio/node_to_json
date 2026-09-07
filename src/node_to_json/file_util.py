from pathlib import Path
from re import findall
from numpy import where, char
from zipfile import ZipFile, is_zipfile, ZIP_LZMA
from typing import Any, Generator, Callable
from io import BytesIO, StringIO
from os import access, F_OK, R_OK, W_OK


class SuspectFileError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


def _is_file_accessible(file_path: str) -> list[bool]:
    return [access(file_path, F_OK), access(file_path, R_OK), access(file_path, W_OK)]


def _is_file_accessible_message(data: list[bool]) -> list[str]:
    msg = "File Path {} {}. "
    if not all(data):
        return [msg.format('is not', 'accessible')]
    exists_ = (msg.format('does', 'exist') if data[0] else msg.format('does not', 'exist'))
    readable_ = (msg.format('is', 'readable') if data[1] else msg.format('is not', 'readable'))
    writeable_ = (msg.format('is', 'writeable') if data[2] else msg.format('is not', 'writeable'))
    return [exists_, readable_, writeable_]


def is_file_accessible(file_path: str) -> dict[str, list[bool] | str]:
    """Retrieve data dict of a file's existance, readability, and writeability.
    
    :param file_path: File path to run check on.
    :type file_path: str
    :return: Dictionary of a files accesibility and a message stating the results
    :rtype: dict[str, list[bool] | str]"""
    acc = _is_file_accessible(file_path)
    return {'access': acc, 'message': "".join(_ for _ in _is_file_accessible_message(acc))}


def read_file(file: str) -> Any:
    """Read data from a file.
    
    :param file: Path of a file to read.
    :type file: str
    :return: Data read from the file.
    :rtype: Any"""
    with open(file, 'r') as f:
        data = f.read()
    return data


def write_file(file: str, data: Any) -> None:
    """Write data to a file.
    
    :param file: Path of a file to write to.
    :type file: str
    :param data: Data to write to file.
    :type data: Any"""
    with open(file, 'w') as f:
        f.write(data)


def get_dir_files(dir_path: str, filter: str='*py') -> Generator[Path, None, None]:
    """Retrieve a generator object of the files in a directory the match the filter.
    
    :param dir_path: Path of the directory to retrieve files from.
    :type dir_path: str
    :param filter: Filter to use for file retrieval.
    :type filter: str
    :return: Generator of the files in the directory that match the filter.
    :rtype: Generator[Path, None, None]"""
    return Path(dir_path).glob(filter)


def get_dir_file_stems(dir_path: str, filter: str='*py', ignore_files: list[str] | None=None) -> Generator[str, None, None]:
    """Retrieve a generator object of the file name stripped of the prefix path.
    
    :param dir_path: Path of the directory to retrieve files from.
    :type dir_path: str
    :param filter: Filter to use for file retrieval.
    :type filter: str
    :param ignore_files: File names to ignore.
    :type ignore_files: list[str] | None
    :return: Description
    :rtype: Generator[str, None, None]"""
    if not ignore_files:
        ignore_files = ['__init__']
    return (file.stem for file in get_dir_files(dir_path, filter=filter) if file.stem not in ignore_files)


def copy_file_by_chunks(src_file: str, target_file: str) -> None:
    """Copy a file in byte chunks.
    
    :param src_file: Source file path to copy data from.
    :type src_file: str
    :param target_file: Target file path to copy data to.
    :type target_file: str"""
    with open(src_file, 'rb') as src:
        with open(target_file, 'wb') as tgt:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                tgt.write(chunk)


def read_file_by_chunks(src_file: str) -> Generator[Any, None, None]:
    """Read a file in byte chunks.
    
    :param src_file: Source file path to read data from.
    :type src_file: str"""
    with open(src_file, 'rb') as src:
        while True:
            chunk = src.read(1024 * 1024)
            if not chunk:
                break
            yield chunk


def write_bytesio(data: bytes) -> BytesIO:
    """Convert bytes data into a BytesIo object.
    
    :param data: Bytes data.
    :type data: bytes
    :return: Bytes data converted to a BytesIO object.
    :rtype: BytesIO"""
    buffer = BytesIO()
    buffer.write(data)
    buffer.seek(0)
    return buffer


def write_stringio(data: str) -> StringIO:
    """Convert string data into a StringIO object.
    
    :param data: String data.
    :type data: str
    :return: String data converted to a StringIO object.
    :rtype: StringIO"""
    buffer = StringIO()
    buffer.write(data)
    buffer.seek(0)
    return buffer


def inject_detect(data: str) -> bool:
    """Check a text string for suspicious characters and function calls.
    
    :param data: Large text string usually read from a file.
    :type data: str
    :return: Result of string check.
    :rtype: bool"""
    s = findall(r'\b(?:os|sys|subprocess|asyncio|pathlib|marshal|ast|cmd|ord|chr)\b', data)
    f = findall(r' eval\(| var\(| exec\(| ord\(| chr\(| -c ', data)
    i = findall(r' os\.| sys\.| subprocess\.| asyncio\.| pathlib\.| marshal\.| ast\.| cmd\.', data)
    check_ = [len(s) > 0, len(f) > 0, len(i) > 0]
    if any(check_):
        print(f"[SUSPICIOUS]: {[_ for idx, _ in enumerate([s, f, i]) if check_[idx]]}")
        return True
    return False


def is_file_suspicious(file: str) -> bool | None:
    """Check a file for suspicious characters and function calls.
    
    :param file: Path of file to check.
    :type file: str
    :return: Return False if checks return False else raise SuspectFileError.
    :rtype: bool | None"""
    data = read_file(file)
    check_ = inject_detect(data)
    if check_:
        raise SuspectFileError(f"Suspect File!!! {Path(file.name)}")
    return check_


def get_from_zip(zip_file: str, file_name: str, is_gen: bool, func: Callable, *args: Any, **kwargs: Any) -> Generator[Any, None, None] | Any | None:
    """Retrieve data from a zip archive.
    
    :param zip_file: Path of a compressed zip archive.
    :type zip_file: str
    :param file_name: Name of file in zip archive.
    :type file_name: str
    :param is_gen: Return a generator object if True else the result of a function func.
    :type is_gen: bool
    :param func: Function to run on file data.
    :type func: Callable
    :param args: Arguments for function func.
    :type args: Any
    :param kwargs: Keyword arguments for function func.
    :type kwargs: Any
    :return: Generator object if is_gen is True else the result of function func or None if the operations fail.
    :rtype: Generator[Any, None, None] | Any"""
    try:
        with ZipFile(zip_file, 'r') as zf:
            with zf.open(file_name) as hf:
                if is_gen:
                    return (_ for _ in list(func(hf, *args, **kwargs)))
                return func(hf, *args, **kwargs)
    except:
        pass


def get_zip_file_list(zip_file: str) -> Generator[str, None, None]:
    """Retrieve the name of the files contained in a zip archive.
    
    :param zip_file: Path of a compressed zip archive.
    :type zip_file: str
    :return: A generator object of the file names
    :rtype: Generator[str, None, None]"""
    with ZipFile(zip_file, 'r') as zf:
        name_list = (f for f in zf.namelist())
    return name_list


def zip_from_folder(src_dir_path: str, dest_dir_path: str) -> None:
    """Copy files from folder into a zip archive.
    
    :param src_dir_path: Source path of files to move to zip archive.
    :type src_dir_path: str
    :param dest_dir_path: Path of the zip archive.
    :type dest_dir_path: str"""
    name = Path(src_dir_path).stem
    zip_name = f"{name}.zip"
    zip_file = Path(dest_dir_path).joinpath(zip_name)
    files_list = Path(src_dir_path).rglob("*")
    with ZipFile(file=zip_file, mode='w', compression=ZIP_LZMA, compresslevel=9) as zf:
        for file in files_list:
            zf.write(filename=file, arcname=file.name)


def zip_append(zip_file: str, file: str, arcname: str | None=None) -> None:
    """Append a file to a zip archive.
    
    :param zip_file: Path of a compressed zip archive.
    :type zip_file: str
    :param file: File to append to zip archive.
    :type file: str
    :param arcname: Name to assign to appended file. If None, the file name is used instead.
    :type arcname: str | None"""
    with ZipFile(zip_file, 'a') as zf:
        name = (Path(file).name if isinstance(arcname, type(None)) else arcname)
        zf.write(file, arcname=name)


def read_from_zip(zip_file: str, file_name: str) -> Any:
    """Read from a file in a zip archive.
    
    :param zip_file: Path of a compressed zip archive.
    :type zip_file: str
    :param file_name: Name of file from zip archive to read.
    :type file_name: str
    :return: Data read from the file.
    :rtype: Any"""
    with ZipFile(zip_file, 'r') as zf:
        with zf.open(zf.namelist()[where(char.find(zf.namelist(), file_name) > -1)[0][0]]) as f:
            data = f.read()
    return data


def create_filler_zip(zip_file: str, file_name: str='USER.txt') -> None:
    """Create a filler file for a zip archive. Useful for creating an empty zip archive since zip archives can not be empty.
    
    :param zip_file: Path of a compressed zip archive.
    :type zip_file: str
    :param file_name: Name for the filler file
    :type file_name: str"""
    with ZipFile(zip_file, 'w', compression=ZIP_LZMA, compresslevel=9, allowZip64=True) as zf:
        zf.writestr(file_name, "")


def write_zip_file_data(file: str, zip_file: str, arcname: str | None=None) -> None:
    """Copy file data to a zip archive.
    
    :param file: Path of file to copy to zip archive.
    :type file: str
    :param zip_file: Path of a compressed zip archive.
    :type zip_file: str
    :param arcname: Name to save file in zip archive. If None use the file name instead.
    :type arcname: str | None"""
    file = Path(file)
    temp_file = Path(f"temp{file.suffix}")
    temp_file.touch(exist_ok=True)
    copy_file_by_chunks(file, temp_file)
    if not arcname:
        arcname = file.name
    zip_file.write(filename=temp_file, arcname=arcname)
    temp_file.unlink()


def zip_data_file(file: str, zip_file: str, arcname: str | None=None) -> None:
    """Write file data to zip archive.
    
    :param file: Path of file to copy to zip archive.
    :type file: str
    :param zip_file: Path of a compressed zip archive.
    :type zip_file: str
    :param arcname: Name to save file in zip archive. If None use the file name instead.
    :type arcname: str | None"""
    with ZipFile(file=zip_file, mode='w', compression=ZIP_LZMA, compresslevel=9) as zf:
        write_zip_file_data(file, zf, arcname=arcname)


def zip_data_files(src_dir_path: str, dest_dir_path: str, filter: str="*py") -> None:
    """Write file data from directory to zip archive.
    
    :param src_dir_path: Source directory to copy files from.
    :type src_dir_path: str
    :param dest_dir_path: Directory to write zip archive to.
    :type dest_dir_path: str
    :param filter: Filter for files in source directory.
    :type filter: str"""
    name = Path(src_dir_path).stem
    zip_name = f"{name}.zip"
    zip_file = Path(dest_dir_path).joinpath(zip_name)
    files_list = Path(src_dir_path).rglob(filter)
    with ZipFile(file=zip_file, mode='w', compression=ZIP_LZMA, compresslevel=9) as zf:
        for file in files_list:
            write_zip_file_data(file, zf)


def append_file_to_zip(src_file: str, zip_file: str, arcname: str | None=None) -> None:
    """Append a file to a zip archive.
    
    :param src_file: Path of file to copy to zip archive.
    :type src_file: str
    :param zip_file: Path of a compressed zip archive.
    :type zip_file: str
    :param arcname: Name to save file in zip archive. If None use the file name instead.
    :type arcname: str | None"""
    if not is_zipfile(zip_file):
        raise ValueError("Destination is not a zip archive!")
    src_file = Path(src_file)
    file_names = set(Path(file).name for file in get_zip_file_list(zip_file))
    if arcname:
        if arcname in file_names:
            raise FileExistsError("File already exists!")
    else:
        if str(src_file.stem) in file_names:
            raise FileExistsError("File already exists!")
    with ZipFile(file=zip_file, mode='a', compression=ZIP_LZMA, compresslevel=9) as zf:
        write_zip_file_data(src_file, zf, arcname=arcname)

