import logging
import time

from abc import ABC, abstractmethod
from pathlib import Path
from threading import Lock
from typing import Optional, Union, List


class _ILogger(ABC):
    @abstractmethod
    def trace(self, message: str) -> None:
        ...


class ILogger:
    level: int
    impl: _ILogger
    tag: str

    def __init__(self, impl: _ILogger, level: int, tag: str):
        self.level = level
        self.impl = impl
        self.tag = tag

    def debug(self, message: str) -> None:
        if self.level <= logging.DEBUG:
            self._trace(message)

    def info(self, message: str) -> None:
        if self.level <= logging.INFO:
            self._trace(message)

    def warning(self, message: str) -> None:
        if self.level <= logging.WARNING:
            self._trace(message)

    def error(self, message: str) -> None:
        if self.level <= logging.ERROR:
            self._trace(message)

    def critical(self, message: str) -> None:
        if self.level <= logging.CRITICAL:
            self._trace(message)

    def _trace(self, message: str) -> None:
        prefix = f'[{time.strftime("%d-%m-%Y %H:%M:%S", time.localtime(time.time()))}]{self.tag}'
        self.impl.trace(f'{prefix} {message}')

    @abstractmethod
    def __getitem__(self, key: str) -> 'ILogger':
        ...


class _ConsoleLoggerImpl(_ILogger):
    lock: Lock

    def __init__(self):
        self.lock = Lock()

    def trace(self, message: str) -> None:
        self.lock.acquire()
        print(message)
        self.lock.release()


class _FileLoggerUnsafe(_ILogger):
    path: Path

    def __init__(self, path: Path):
        self.path = path

    def trace(self, message: str) -> None:
        with open(self.path, 'a') as f:
            f.write(f'{message}\n')


class _FileLoggerSafe(_ILogger):
    lock: Lock
    path: Path

    def __init__(self, path: Path):
        self.lock = Lock()
        self.unsafe = _FileLoggerUnsafe(path)

    def trace(self, message: str) -> None:
        self.lock.acquire()
        self.unsafe.trace(message)
        self.lock.release()


class ConsoleLogger(ILogger):
    level_str: str

    def __init__(self, level: str = 'INFO', tag: str = '', impl: _ILogger = _ConsoleLoggerImpl()):
        self.level_str = level
        super().__init__(impl, logging.getLevelName(self.level_str), tag)

    def __getitem__(self, key: str) -> 'ConsoleLogger':
        return ConsoleLogger(self.level_str, f'{self.tag}[{key}]', self.impl)
    
    def trace(self, message: str) -> None:
        self.impl.trace(message)


class FileLogger(ILogger):
    level_str: str

    def __init__(self,
                 path: Optional[Union[str, Path]],
                 level: str = 'INFO',
                 tag: str = '',
                 impl: Optional[_ILogger] = None):
        self.level_str = level
        if not impl:
            Path(path).parent.mkdir(exist_ok=True, parents=True)
            impl = _FileLoggerSafe(Path(path))
        super().__init__(impl, logging.getLevelName(self.level_str), tag)

    def __getitem__(self, key: str) -> 'FileLogger':
        return FileLogger(path=None, level=self.level_str, tag = f'{self.tag}[{key}]', impl=self.impl)
    
    def trace(self, message: str) -> None:
        self.impl.trace(message)


class MultiFileLogger(ILogger):
    level_str: str
    folder: Path

    def __init__(self, folder: Union[str, Path], level: str = 'INFO'):
        self.level_str = level
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        impl = _FileLoggerUnsafe(self.folder.joinpath(f'log.txt'))
        super().__init__(impl, logging.getLevelName(self.level_str), None)

    def __getitem__(self, key: str) -> 'MultiFileLogger':
        return MultiFileLogger(folder=self.folder.joinpath(key), level=self.level_str)
    
    def trace(self, message: str) -> None:
        self.impl.trace(message)


class MultiLogger:
    def __init__(self, loggers: List[ILogger]):
        self.loggers = loggers

    def debug(self, message: str) -> None:
        for logger in self.loggers:
            logger.debug(message)

    def info(self, message: str) -> None:
        for logger in self.loggers:
            logger.info(message)

    def warning(self, message: str) -> None:
        for logger in self.loggers:
            logger.warning(message)

    def error(self, message: str) -> None:
        for logger in self.loggers:
            logger.error(message)

    def critical(self, message: str) -> None:
        for logger in self.loggers:
            logger.critical(message)

    def __getitem__(self, key: str) -> 'MultiLogger':
        return MultiLogger([logger[key] for logger in self.loggers])
