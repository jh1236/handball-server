from typing import TypeVar

T = TypeVar('T')


def chunks_sized(lst: list[T], n: int) -> list[list[T]]:
    """Yield successive n-sized chunks from lst."""
    lizt = []
    for i in range(0, len(lst), n):
        lizt.append(lst[i:i + n])
    return lizt


def n_chunks(l: list[T], n: int, s=None) -> list[list[T]]:
    """Yield n number of striped chunks from l. """
    l = l.copy()
    while s and len(l) % n != 0:
        l.append(s)
    for i in range(0, n):
        yield l[i::n]


class Console:
    def __init__(self):
        self.print = True
        self.file = "./resources/latest.log"
        self.info = self.add_log("info")
        self.warn = self.add_log("warn")
        self.error = self.add_log("error")
        self.fatal = self.add_log("fatal")

    def add_log(self, level):
        def x(message: str):
            s = f"[{level.upper()}: ] {message}\n"
            if self.print:
                print(s, end="")
            with open(self.file, "a+") as fp:
                fp.write(s)

        return x

    def clear(self):
        with open(self.file, "w+") as fp:
            fp.write("")


con: Console = Console()


def get_console() -> Console:
    return con
