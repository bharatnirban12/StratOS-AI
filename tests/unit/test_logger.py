from shared.utils.logger import get_logger


def test_logger():
    log = get_logger(service="test")

    log.info("Test log")

    assert True  # if no crash → pass