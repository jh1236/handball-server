from collections import defaultdict
from typing import List, Dict, Tuple

from structure.Game import Game
from structure.Team import BYE, Team
from tournaments.FixtureMaker import FixtureMaker
from utils.logging_handler import logger


class Swiss(FixtureMaker):
    def __init__(self, tournament, rounds=8):
        super().__init__(tournament)
        self.teams_fixed = tournament.teams.copy()
        if len(self.teams_fixed) % 2 == 1:
            self.teams_fixed.append(BYE)
        self.round_count = rounds
        self.max_rounds = len(self.teams_fixed) - 1

    def get_generator(self):
        """Generates each round of the competition

        Yields:
            List[Game]: The round which has been generated
        """
        for _ in range(self.round_count):
            yield self.match_make()

    def match_make(self) -> List[Game]:
        """
        Raises:
            Exception: When all games have been generated there are no options for any more.

        Returns:
            List[Game]: A compilation of all matches for the given round.
        """
        if len(self.teams_fixed[0].teams_played) + 1 == len(self.teams_fixed):
            raise Exception("All games have been played")

        roster = []

        unfilled = sorted(self.teams_fixed, key=lambda x: (x.games_won, x.points_for - x.points_against))

        counter = 0  # used to count how many attempts are made before we turn to the fallback method.
        while unfilled:
            target = unfilled.pop(0)

            for i, team in enumerate(unfilled):
                if not target.has_played(team):
                    roster.append(x := [target, unfilled.pop(i)])
                    break
            else:
                # could not find a unique match, 
                # put them on the end of the array.
                unfilled.append(target)

            counter += 1
            if counter > (len(self.teams_fixed) * 2):
                roster = self.fallback()
                unfilled = False

        if not roster:  # if some-how we end up here, just pair the best performing teams together.
            logger.error("COULD NOT GENERATE UNIQUE MATCH. PAIRING BEST TEAMS")
            unfilled = sorted(self.teams_fixed, key=lambda x: (x.games_won, x.points_for - x.points_against))
            roster = [unfilled[a:a + 2] for a in range(0, len(unfilled), 2)]

        # turn the proposed games into game objects
        final_roster = []
        for j in roster:
            final_roster.append(Game(j[0], j[1], self.tournament))

        return final_roster

    def get_possible_pairs(self) -> Dict[Team, List[Team]]:
        """finds all teams that have not played eachother yet.

        Returns:
            Dict[Team, List[Team]]: Relationship of all teams that have not played eachother yet
        """
        possible_pairs = defaultdict(list)
        for j in self.teams_fixed:
            for k in self.teams_fixed:
                if not j.has_played(k) and j != k:
                    possible_pairs[j].append(k)
        return possible_pairs

    def fallback(self) -> Tuple[Team, Team]:
        """Starter function for the fallback method of finding matches, equivilant to round robin

        Returns:
            Tuple[Team, Team]: the array of matches to be sent to self.match_make(), to be converted to Game objects
        """
        possible_pairs = self.get_possible_pairs()

        used = []
        games = []
        self.find_unique_recursive(games, used, possible_pairs)
        return games

    def get_available_teams(self, used: List[Team], teams: List[Team] = None) -> List[Team]:
        """filters out teams which are already being used, allowing for simpler code and a small amount of
        optimisations

        Args:
            used (List[Team]): All the teams that are "not available"
            teams (List[Team], optional): The teams that are to be chosen from. Defaults to all aeams.

        Returns:
            List[Team]: All the teams that are "available" to be chosen
        """
        if teams is None:
            teams = self.teams_fixed
        return [team for team in teams if team not in used]

    def find_unique_recursive(self, games: List[Tuple[Team, Team]], used: List[Team],
                              possible_pairs: Dict[Team, List[Team]]) -> None:
        """brute forces all combinations of possible matches to find one that has not been played before

        Args:
            games (List[Tuple[Team, Team]]): A collection of the current proposed games
            used (List[Team]): A collection of all teams that are in proposed games to easily prevent duplicate teams
            possible_pairs (Dict[Team, List[Team]]): A relationship of all teams that have not played eachother yet
        """
        for team in self.get_available_teams(used):
            used.append(team)
            for other_team in self.get_available_teams(used, possible_pairs[team]):
                games.append((team, other_team))
                used.append(other_team)
                if len(used) != len(self.teams_fixed):
                    self.find_unique_recursive(games, used, possible_pairs)
                if len(used) == len(self.teams_fixed):
                    return
                used.pop()
                games.pop()
            used.pop()
