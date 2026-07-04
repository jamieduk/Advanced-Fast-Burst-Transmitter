import logging
import os
import sys
from datetime import datetime
from typing import Optional


class Logger:
    _instance: Optional['Logger']=None
    _initialized: bool=False

    def __new__(cls) -> 'Logger':
        if cls._instance is None:
            cls._instance=super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if Logger._initialized:
            return
        Logger._initialized=True
        self._logger=logging.getLogger("AudioBurst")
        self._logger.setLevel(logging.DEBUG)
        self._file_handler: Optional[logging.FileHandler]=None
        self._console_handler: logging.StreamHandler=logging.StreamHandler(sys.stdout)
        self._console_handler.setLevel(logging.INFO)
        console_fmt=logging.Formatter('[%(levelname)s] %(message)s')
        self._console_handler.setFormatter(console_fmt)
        self._logger.addHandler(self._console_handler)

    def setup_file_logging(self, log_file: str, level: str="INFO") -> None:
        os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
        if self._file_handler:
            self._logger.removeHandler(self._file_handler)
        self._file_handler=logging.FileHandler(log_file)
        self._file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        file_fmt=logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
        self._file_handler.setFormatter(file_fmt)
        self._logger.addHandler(self._file_handler)

    def set_level(self, level: str) -> None:
        self._console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    def debug(self, msg: str) -> None:
        self._logger.debug(msg)

    def info(self, msg: str) -> None:
        self._logger.info(msg)

    def warning(self, msg: str) -> None:
        self._logger.warning(msg)

    def error(self, msg: str) -> None:
        self._logger.error(msg)

    def critical(self, msg: str) -> None:
        self._logger.critical(msg)


log=Logger()
