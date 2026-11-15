import logging


class RLogger:
    def __init__(self, module_name: str) -> None:
        self._module = module_name
        self._logger = logging.getLogger(self._module)
        self._formatter = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    @property
    def _console_handler(self) -> logging.StreamHandler:
        formatter = logging.Formatter(self._formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        return console_handler

    def info(self, msg: str) -> None:
        console_logger = self._logger

        console_logger.addHandler(self._console_handler)
        console_logger.setLevel(logging.INFO)
        return console_logger.info(msg)

    def _debug_handler(self, msg: str) -> None:
        console_logger = self._logger

        console_logger.addHandler(self._console_handler)
        console_logger.setLevel(logging.INFO)
        return console_logger.debug(msg)
