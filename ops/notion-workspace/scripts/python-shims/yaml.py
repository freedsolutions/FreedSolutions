class YAMLError(Exception):
    pass


def _strip_quotes(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def safe_load(text):
    data = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise YAMLError(f"Unsupported YAML line: {raw_line}")

        key, value = line.split(":", 1)
        key = key.strip()
        value = _strip_quotes(value.strip())

        if not key:
            raise YAMLError(f"Missing key in line: {raw_line}")

        data[key] = value

    return data
