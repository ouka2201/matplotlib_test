def chunks(iterable, size):
    for i in range(0, len(iterable), size):
        yield iterable[i:i + size]


from itertools import islice

def chunks(iterable, size):
    it = iter(iterable)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            break
        yield chunk
