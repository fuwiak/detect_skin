"""
Утилиты для работы с таймаутами
"""
import threading
import logging

logger = logging.getLogger(__name__)


class TimeoutException(Exception):
    """Исключение при превышении времени ожидания SAM3"""
    pass


def run_with_timeout(func, timeout: int, *args, **kwargs):
    """Запускает функцию в отдельном потоке и обрывает при превышении таймаута"""
    result_container = {"result": None, "error": None}

    def target():
        try:
            result_container["result"] = func(*args, **kwargs)
        except Exception as e:
            result_container["error"] = e

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        return None, TimeoutException(f"Превышено время ожидания {timeout}с")
    if result_container["error"]:
        return None, result_container["error"]
    return result_container["result"], None




