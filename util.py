from typing import TypeVar

T = TypeVar('T')


def chunks_sized(lst: list[T], n: int) -> list[list[T]]:
    """Yield successive n-sized chunks from lst."""
    lizt = []
    for i in range(0, len(lst), n):
        lizt.append(lst[i:i + n])
    return lizt


def n_chunks(l: list[T], n: int, s=None) -> list[list[T]]:
    """Yield n number of striped chunks from l.
    """
    l = l.copy()
    while s and len(l) % n != 0:
        l.append(s)
    for i in range(0, n):
        yield l[i::n]
