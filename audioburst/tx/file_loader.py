import os
import tarfile
import io
import zlib
from typing import Optional, Tuple, List
from audioburst.utils.logger import log


def load_file(filepath: str) -> Optional[bytes]:
    if not os.path.isfile(filepath):
        log.error(f"File not found: {filepath}")
        return None
    try:
        with open(filepath, 'rb') as f:
            return f.read()
    except Exception as e:
        log.error(f"Failed to read file {filepath}: {e}")
        return None


def get_file_info(filepath: str) -> Tuple[str, int]:
    filename=os.path.basename(filepath)
    size=os.path.getsize(filepath)
    return filename, size


def pack_folder(folder_path: str, compression: bool=True) -> Optional[bytes]:
    if not os.path.isdir(folder_path):
        log.error(f"Folder not found: {folder_path}")
        return None
    try:
        buf=io.BytesIO()
        mode='w:gz' if compression else 'w'
        with tarfile.open(fileobj=buf, mode=mode) as tar:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    full_path=os.path.join(root, file)
                    arcname=os.path.relpath(full_path, os.path.dirname(folder_path))
                    tar.add(full_path, arcname=arcname)
        return buf.getvalue()
    except Exception as e:
        log.error(f"Failed to pack folder {folder_path}: {e}")
        return None


def unpack_folder(data: bytes, output_dir: str) -> bool:
    try:
        buf=io.BytesIO(data)
        mode='r:gz' if data[:2] == b'\x1f\x8b' else 'r'
        with tarfile.open(fileobj=buf, mode=mode) as tar:
            tar.extractall(path=output_dir)
        return True
    except Exception as e:
        log.error(f"Failed to unpack folder: {e}")
        return False


def list_folder_contents(folder_path: str) -> List[str]:
    result=[]
    if not os.path.isdir(folder_path):
        return result
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            full_path=os.path.join(root, file)
            result.append(os.path.relpath(full_path, folder_path))
    return result


def prepare_transmission_data(path: str) -> Tuple[bytes, str, bool]:
    is_folder=os.path.isdir(path)
    if is_folder:
        data=pack_folder(path)
        name=os.path.basename(path.rstrip('/'))
        if data is None:
            return b'', name, True
        return data, name, True
    else:
        data=load_file(path)
        name=os.path.basename(path)
        if data is None:
            return b'', name, False
        return data, name, False
