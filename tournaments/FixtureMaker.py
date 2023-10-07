from typing import Generator, Type

from structure.Game import Game


class FixtureMaker:
    def __init__(self, tournament):
        self.tournament = tournament

    def get_generator(self) -> Generator[list[Game], None, None]:
        raise NotImplementedError("Function not implemented!")

    @classmethod
    def get_name(cls):
        return cls.__name__


def get_type_from_name(name: str) -> Type[FixtureMaker]:
    from tournaments.BasicFinals import BasicFinals
    from tournaments.SecondChanceFinals import SecondChanceFinals
    from tournaments.Swiss import Swiss
    from tournaments.RoundRobin import RoundRobin
    return {
        BasicFinals.get_name(): BasicFinals,
        SecondChanceFinals.get_name(): SecondChanceFinals,
        Swiss.get_name(): Swiss,
        RoundRobin.get_name(): RoundRobin
    }[name]
