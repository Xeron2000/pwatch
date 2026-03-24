from pwatch.exchanges.okx import OkxExchange


def test_extract_price_prefers_last_field():
    item = {"last": "123.45", "instId": "BTC-USDT-SWAP"}

    assert OkxExchange._extract_price(item) == 123.45


def test_extract_price_falls_back_to_last_price_field():
    item = {"lastPrice": "234.56", "instId": "BTC-USDT-SWAP"}

    assert OkxExchange._extract_price(item) == 234.56
