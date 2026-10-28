TAX_PERCENT = 10


def load_rate(config, key):
    return config.get(key, 0)


def total(items, config):
    out = 0
    for item in items:
        out += item["amount"] * load_rate(config, item["kind"])
    return out


def describe(n):
    if n > 0:
        return "plus"
    if n == 0:
        return "zero"
    if n > 0:
        return "plus"
    return "minus"


def with_tax(amount_yen):
    return amount_yen + amount_yen * TAX_PERCENT // 100
