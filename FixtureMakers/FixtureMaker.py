from typing import Generator, Type

from structure.Game import Game


class FixtureMaker:
    def __init__(self, tournament):
        self.tournament = tournament

    def get_generator(self) -> Generator[list[Game], None, None]:
        raise NotImplementedError("Function not implemented!")

    @classmethod
    def manual_allowed(cls):
        return False

    @classmethod
    def get_name(cls):
        return cls.__name__


class Empty(FixtureMaker):
    def get_generator(self) -> Generator[list[Game], None, None]:
        return None


def get_type_from_name(name: str) -> Type[FixtureMaker]:
    from FixtureMakers.BasicFinals import BasicFinals
    from FixtureMakers.SecondChanceFinals import SecondChanceFinals
    from FixtureMakers.Swiss import Swiss
    from FixtureMakers.RoundRobin import RoundRobin
    from FixtureMakers.OneRound import OneRound
    from FixtureMakers.Pooled import Pooled


    return {
        BasicFinals.get_name(): BasicFinals,
        SecondChanceFinals.get_name(): SecondChanceFinals,
        Swiss.get_name(): Swiss,
        RoundRobin.get_name(): RoundRobin,
        OneRound.get_name(): OneRound,
        "None": Empty,
        Pooled.get_name(): Pooled,
    }[name]
