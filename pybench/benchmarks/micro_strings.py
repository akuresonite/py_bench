"""String formatting and manipulation."""

GROUP = "micro"


def bench_str_fstring(loops):
    """f-string interpolation of mixed types."""
    name = "benchmark"
    value = 42
    ratio = 1.5
    out = None
    for i in range(loops):
        out = f"{name}:{value}:{ratio:.2f}:{i}"
    return out


def bench_str_format(loops):
    """str.format interpolation."""
    template = "{}:{}:{:.2f}:{}"
    out = None
    for i in range(loops):
        out = template.format("benchmark", 42, 1.5, i)
    return out


def bench_str_concat(loops):
    """Repeated concatenation, flushed to bound memory."""
    out = ""
    for i in range(loops):
        out += "x"
        if len(out) >= 512:
            out = ""
    return len(out)


def bench_str_join(loops):
    """str.join over a list of parts."""
    parts = ["alpha", "beta", "gamma", "delta", "epsilon"]
    sep = "-"
    out = None
    for _ in range(loops):
        out = sep.join(parts)
    return out


def setup_str_methods():
    return "The quick brown fox jumps over the lazy dog, repeatedly and often."


def bench_str_methods(loops, state):
    """split / replace / upper on a short sentence."""
    text = state
    out = None
    for _ in range(loops):
        out = text.replace("quick", "slow").upper().split(" ")
    return out


def bench_str_startswith(loops):
    """startswith and endswith checks."""
    text = "https://example.invalid/path/to/resource"
    total = 0
    for _ in range(loops):
        if text.startswith("https://"):
            total += 1
        if text.endswith(".png"):
            total += 1
    return total


def bench_str_encode_decode(loops):
    """UTF-8 round trip."""
    text = "hello wörld — benchmark"
    out = None
    for _ in range(loops):
        out = text.encode("utf-8").decode("utf-8")
    return out
