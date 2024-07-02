import time
from collections import defaultdict
from dataclasses import dataclass

from flask import render_template, request

from Config import Config
from FixtureGenerators.FixturesGenerator import get_type_from_name
from database.models import People, PlayerGameStats, Games
from structure import manage_game
from structure.AllTournament import (
    get_all_officials,
)
from structure.GameUtils import game_string_to_commentary
from structure.get_information import get_tournament_id
from utils.databaseManager import DatabaseManager
from utils.permissions import (
    fetch_user,
    officials_only,
    user_on_mobile,
)  # Temporary till i make a function that can handle dynamic/game permissions
from utils.sidebar_wrapper import render_template_sidebar, link
from utils.util import fixture_sorter
from website.website import numbers



def priority_to_classname(p):
    if p == 1:
        return ""
    sizes = ["sm", "md", "lg", "xl"]
    return f"d-none d-{sizes[p - 2]}-table-cell"


def add_tournament_specific(app):
    @app.get("/<tournament>/")  # TODO: Implement pooled
    def home_page(tournament: str):
        tournament_id: int = get_tournament_id(tournament)
        if tournament_id is None:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This is not a real tournament",
                ),
                400,
            )

        @dataclass
        class Tourney:
            name: str
            searchableName: str
            editable: str

        # ladder
        @dataclass
        class LadderTeam:
            name: str
            searchableName: str
            games_won: int
            games_played: int
            pool: int

        @dataclass
        class Game:
            teams: list[str]
            score_string: str
            id: int

        @dataclass
        class Player:
            name: str
            searchableName: str
            best: int
            points: int
            aces: int
            cards: int

        with DatabaseManager() as c:
            teams = c.execute(
                """
                            SELECT 
                                name, teams.searchable_name, SUM(games.winning_team_id = teams.id) as gamesWon, COUNT(games.id) as gamesPlayed, pool 
                                FROM tournamentTeams 
                                INNER JOIN teams ON tournamentTeams.team_id = teams.id
                                INNER JOIN games ON (teams.id = games.team_one_id OR teams.id = games.team_two_id) AND tournamentTeams.tournament_id = games.tournament_id 
                                WHERE games.tournament_id = ? AND NOT games.is_final AND NOT games.is_bye
                                group by teams.id 
                                ORDER BY 
                                    CAST(gamesWon AS REAL) / gamesPlayed DESC, gamesPlayed DESC  
                                LIMIT 10;""",
                (tournament_id,),
            ).fetchall()
            tourney = c.execute(
                "SELECT name, searchable_name, fixtures_type, is_pooled from tournaments where id = ?",
                (tournament_id,),
            ).fetchone()

            ladder = [LadderTeam(*team) for team in teams]

            if tourney[3]:  # this tournament is pooled
                ladder = [
                    (
                        f"Pool {numbers[i]}",
                        list(enumerate((j for j in ladder if j.pool == i), start=1)),
                    )
                    for i in range(1, 3)
                ]
            else:
                ladder = [("", list(enumerate(ladder, start=1)))]

            # there has to be a reason this is the required syntax but i can't work it out1

            games = c.execute(
                """         SELECT 
                                serving.name, receiving.name, team_one_score, team_two_score, games.id 
                                FROM games 
                                INNER JOIN teams AS serving ON games.team_one_id = serving.id 
                                INNER JOIN teams as receiving ON games.team_two_id = receiving.id 
                                WHERE 
                                    tournament_id = ? AND not games.ended AND NOT games.is_bye AND games.round = (SELECT MAX(inn.round) FROM games inn WHERE inn.tournament_id = games.tournament_id);
                            """,
                (tournament_id,),
            ).fetchall()
            ongoing_games = [
                Game(game[:2], f"{game[2]} - {game[3]}", game[4]) for game in games
            ]

            games = c.execute(
                """
                            SELECT 
                                serving.name, receiving.name, team_one_score, team_two_score, games.id
                                FROM games 
                                INNER JOIN teams AS serving ON games.team_one_id = serving.id 
                                INNER JOIN teams as receiving ON games.team_two_id = receiving.id 
                                WHERE tournament_id = ? AND
                                CASE -- if there is finals, return the finals, else return the last round
                                    WHEN (SELECT count(*) FROM games WHERE tournament_id = ? AND is_final = 1) > 0 THEN
                                        is_final = 1
                                    ELSE 
                                        round = (SELECT max(round) FROM games WHERE tournament_id = ?) 
                                END;""",
                (tournament_id,) * 3,
            ).fetchall()
            current_round = [
                Game(game[:2], f"{game[2]} - {game[3]}", game[4]) for game in games
            ]

            playerList = c.execute(
                """
                                SELECT 
                                    people.name, searchable_name, coalesce(sum(games.best_player_id = people.id), 0) as isBestPlayer, coalesce(sum(points_scored), 0), coalesce(sum(aces_scored), 0), coalesce(sum(red_cards+yellow_cards), 0) 
                                    FROM people 
                                    LEFT JOIN playerGameStats ON player_id = people.id
                                    LEFT JOIN games ON playerGameStats.game_id = games.id 
                                    WHERE 
                                        playerGameStats.tournament_id = ? AND
                                        (is_final = 0 OR is_final is null) AND searchable_name <> 'null'
                                    GROUP BY player_id 
                                    ORDER BY 
                                        isBestPlayer DESC, 
                                        sum(points_scored) DESC, 
                                        sum(aces_scored) DESC, 
                                        sum(red_cards+yellow_cards+green_cards) ASC  
                                    LIMIT 10;""",
                (tournament_id,),
            ).fetchall()
            players = [Player(*player) for player in playerList]

            notes = (
                    c.execute(
                        "SELECT notes FROM tournaments WHERE id = ?", (tournament_id,)
                    ).fetchone()[0]
                    or "Notices will appear here when posted"
            )
            in_progress = c.execute(
                "SELECT not(finished) FROM tournaments WHERE id=?", (tournament_id,)
            ).fetchone()[0]
            iseditable = get_type_from_name(tourney[2], tournament_id).manual_allowed()
            tourney = Tourney(tourney[0], tourney[1], iseditable)

            return (
                render_template_sidebar(
                    "tournament_specific/tournament_home.html",
                    tourney=tourney,
                    ongoing=ongoing_games,
                    current_round=current_round,
                    players=players,
                    notes=notes,
                    in_progress=in_progress,
                    ladder=ladder,
                ),
                200,
            )

    @app.get("/<tournament>/fixtures/")
    def fixtures(tournament):
        tournament_id = get_tournament_id(tournament)
        with DatabaseManager() as c:
            games = c.execute(
                """
                            SELECT 
                                games.id, court, is_bye, serving.name, receiving.name, team_one_score, team_two_score, round
                                FROM games 
                                INNER JOIN teams serving ON games.team_one_id = serving.id
                                INNER JOIN teams receiving ON games.team_two_id = receiving.id
                                -- INNER JOIN people ON games.bestPlayer = people.id 
                                WHERE 
                                    tournament_id = ? AND
                                    is_final = 0;""", (tournament_id,)
            ).fetchall()

            # me when i criticize Jareds code then write this abomination

            @dataclass
            class Game:
                teams: list[str]
                score_string: str
                id: int
                court: int
                bye: bool

            # me when i criticize Jareds code then write this abomination
            fixtures = defaultdict(list)
            for game in games:
                fixtures[game[-1]].append(
                    Game(game[3:5], f"{game[5]} - {game[6]}", game[0], game[1], game[2])
                )
            new_fixtures = {}
            for k, v in fixtures.items():
                new_fixtures[k] = [j[3] for j in fixture_sorter([(i.id, i.court, i.bye, i) for i in v])]
            fixtures = new_fixtures

            games = c.execute(
                """
                            SELECT 
                                games.id, court, is_bye, serving.name, receiving.name, team_one_score, team_two_score, round
                                FROM games 
                                INNER JOIN teams serving ON games.team_one_id = serving.id
                                INNER JOIN teams receiving ON games.team_two_id = receiving.id
                                -- INNER JOIN people ON games.bestPlayer = people.id 
                                WHERE 
                                        tournament_id = ? AND
                                        is_final = 1;""",
                (tournament_id,),
            ).fetchall()
            # idk something about glass houses?
            finals = defaultdict(list)
            for game in games:
                finals[game[-1]].append(
                    Game(game[3:5], f"{game[5]} - {game[6]}", game[0], game[1], game[2])
                )
        return (
            render_template_sidebar(
                "tournament_specific/site.html",
                fixtures=fixtures.items(),
                finals=finals.items(),
            ),
            200,
        )

    @app.get("/<tournament>/fixtures/detailed")
    def detailed_fixtures(tournament):
        # TODO: jared said he wanted to do this, Thanks :)

        # court = request.args.get("court", None, type=int)
        # round = request.args.get("round", None, type=int)
        # umpire = request.args.get("umpire", None, type=str)
        # team = request.args.get("team", None, type=str)
        # player = request.args.get("player", None, type=str)
        @dataclass
        class GameDetailed:
            teams: list[str]
            score_string: str
            id: int
            bye: bool
            umpire: str
            umpireSearchableName: str
            scorer: str
            scorerSearchableName: str
            court: int
            court_name: str

        @dataclass
        class Tourney:
            two_courts: bool
            scorer: bool

        with DatabaseManager() as c:
            tournament_id = get_tournament_id(tournament)

            games = c.execute(
                """SELECT 
                        games.id, court, is_bye, serving.name, receiving.name, team_one_score, team_two_score, 
                        umpire.name, umpire.searchable_name, scorer.name, scorer.searchable_name, 
                        round
                        FROM games 
                        INNER JOIN teams AS serving ON games.team_one_id = serving.id 
                        INNER JOIN teams AS receiving ON games.team_two_id = receiving.id
                        LEFT JOIN officials AS u ON games.official_id = u.id
                            LEFT JOIN people AS umpire ON u.person_id = umpire.id
                        LEFT JOIN officials AS s ON games.scorer_id = s.id
                            LEFT JOIN people AS scorer ON s.person_id = scorer.id
                        WHERE
                            tournament_id = ? AND
                            is_final = 0;
                            """,
                (tournament_id,),
            )
            fixtures = defaultdict(list)
            for game in games:
                fixtures[game[-1]].append(
                    GameDetailed(
                        game[3:5],
                        f"{game[5]} - {game[6]}",
                        game[0],
                        game[2],
                        game[7],
                        game[8],
                        game[9],
                        game[10],
                        game[1],
                        {-1: "-", 0: "Court 1", 1: "Court 2"}.get(game[1]),
                    )
                )

            new_fixtures = {}
            for k, v in fixtures.items():
                new_fixtures[k] = [j[3] for j in fixture_sorter([(i.id, i.court, i.bye, i) for i in v])]
            fixtures = new_fixtures

            games = c.execute(
                """SELECT 
                        games.id, court, is_bye, serving.name, receiving.name, team_one_score, team_two_score, 
                        umpire.name, umpire.searchable_name, scorer.name, scorer.searchable_name, 
                        round
                        FROM games 
                        INNER JOIN teams AS serving ON games.team_one_id = serving.id 
                        INNER JOIN teams AS receiving ON games.team_two_id = receiving.id
                        LEFT JOIN officials AS u ON games.official_id = u.id
                            LEFT JOIN people AS umpire ON u.person_id = umpire.id
                        LEFT JOIN officials AS s ON games.scorer_id = s.id
                            LEFT JOIN people AS scorer ON s.person_id = scorer.id
                        WHERE
                            tournament_id = ? AND
                            is_final = 1;""",
                (tournament_id,),
            )
            finals = defaultdict(list)
            for game in games:
                finals[game[-1]].append(
                    GameDetailed(
                        game[3:5],
                        f"{game[5]} - {game[6]}",
                        game[0],
                        game[2],
                        game[7],
                        game[8],
                        game[9],
                        game[10],
                        game[1],
                        {-1: "-", 0: "Court 1", 1: "Court 2"}.get(game[1]),
                    )
                )

            t = Tourney(
                *c.execute(
                    """SELECT
                                two_courts, has_scorer
                                FROM tournaments
                                INNER JOIN games ON games.tournament_id = tournaments.id
                                WHERE tournaments.id = ?;""",
                    (tournament_id,),
                ).fetchone()
            )

        return (
            render_template_sidebar(
                "tournament_specific/site_detailed.html",
                fixtures=fixtures.items(),
                finals=finals.items(),
                t=t,
                reset=False  # TODO: see todo above
                # reset=court is not None
                # or round is not None
                # or umpire is not None
                # or team is not None
                # or player is not None,
            ),
            200,
        )

    @app.get("/<tournament>/teams/")
    def team_directory_site(tournament):
        @dataclass
        class Team:
            name: str
            searchableName: str
            image: str

        with DatabaseManager() as c:
            tournament_id = get_tournament_id(tournament)
            teams = c.execute(
                """
                            SELECT 
                                name, searchable_name, 
                                    case 
                                        when image_url is null 
                                            then '/api/teams/image?name=blank' 
                                        else 
                                            image_url
                                    end  
                                FROM teams 
                                INNER JOIN tournamentTeams ON teams.id = tournamentTeams.team_id 
                                WHERE IIF(? is NULL, 1, tournament_id = ?) GROUP BY teams.id ORDER BY searchable_name""",
                (tournament_id, tournament_id),
            ).fetchall()
            teams = [Team(*team) for team in teams]

        return (
            render_template_sidebar(
                "tournament_specific/stats.html",
                teams=teams,
            ),
            200,
        )

    @app.get("/<tournament>/teams/<team_name>/")
    def team_site(tournament, team_name):
        tournament_id = get_tournament_id(tournament)

        @dataclass
        class TeamStats:
            name: str
            searchableName: str
            image: str
            stats: dict[str, object]

        team_headers = [
            "Elo",
            "Games Played",
            "Games Won",
            "Games Lost",
            "Percentage",
            "Green Cards",
            "Yellow Cards",
            "Red Cards",
            "Faults",
            "Timeouts Called",
            "Points Scored",
            "Points Against",
            "Point Difference",
        ]

        @dataclass
        class PlayerStats:
            name: str
            searchableName: str
            stats: dict[str, object]

        player_headers = ["B&F Votes",
                          "Elo",
                          "Points scored",
                          "Aces scored",
                          "Faults",
                          "Double Faults",
                          "Green Cards",
                          "Yellow Cards",
                          "Red Cards",
                          "Rounds on Court",
                          "Rounds Carded",
                          "Net Elo Delta",
                          "Average Elo Delta",
                          "Points served",
                          "Points Per Game",  # ppg
                          "Points Per Loss",
                          "Aces Per Game",
                          "Faults Per Game",
                          "Cards Per Game",
                          "Cards",
                          "Points Per Card",
                          "Serves Per Game",
                          "Serves Per Ace",
                          "Serves Per Fault",
                          "Serve Ace Rate",
                          "Serve Fault Rate",
                          "Percentage of Points scored",
                          "Percentage of Points scored for Team",
                          "Percentage of Games as Left Player",
                          "Serving Conversion Rate",
                          # "Average Serving Streak",
                          # "Max. Serving Streak",
                          # "Max. Ace Streak",
                          "Serves Received",
                          "Serves Returned",
                          "Return Rate",
                          "Votes Per 100 Games"]

        with DatabaseManager() as c:
            team = c.execute(
                """SELECT teams.name,
       teams.searchable_name,
       case
           when teams.image_url is null
               then '/api/teams/image?name=blank'
           else
               teams.image_url
           end,
       ROUND(1500.0 + coalesce((SELECT SUM(elo_delta)
                                from eloChange
                                         INNER JOIN teams inside ON inside.id = teams.id
                                         INNER JOIN people captain ON captain.id = inside.captain_id
                                         LEFT JOIN people non_captain ON non_captain.id = inside.non_captain_id
                                         LEFT JOIN people sub ON sub.id = inside.substitute_id
                                where eloChange.player_id = sub.id
                                   or eloChange.player_id = captain.id
                                   or eloChange.player_id = non_captain.id AND eloChange.game_id <= MAX(games.id)), 0)
           /
                      COUNT(teams.captain_id is not null + teams.non_captain_id is not null + teams.substitute_id is not null),
             2) as elo,
       COUNT(DISTINCT games.id),
       COUNT(DISTINCT IIF(games.winning_team_id = teams.id, games.id, NULL)),
       COUNT(DISTINCT playerGameStats.game_id) - COUNT(DISTINCT IIF(games.winning_team_id = teams.id, games.id, NULL)),
       ROUND(100.0 * Cast(COUNT(DISTINCT IIF(games.winning_team_id = teams.id, games.id, NULL)) AS REAL) /
             COUNT(DISTINCT playerGameStats.game_id),
             2) || '%',
       coalesce(SUM(playerGameStats.green_cards), 0),
       coalesce(SUM(playerGameStats.yellow_cards), 0),
       coalesce(SUM(playerGameStats.red_cards), 0),
       coalesce(SUM(playerGameStats.faults), 0),
       coalesce(SUM((SELECT IIF(games.team_one_id = teams.id, games.team_one_timeouts, games.team_two_timeouts)
                     FROM games
                     WHERE games.id = game_id
                       AND player_id = teams.captain_id)), 0),
       coalesce(SUM((SELECT IIF(games.team_one_id = teams.id, games.team_one_score, games.team_two_score)
                     FROM games
                     WHERE games.id = game_id
                       AND player_id = teams.captain_id)), 0),
       coalesce(SUM((SELECT IIF(games.team_one_id = teams.id, games.team_two_score, games.team_one_score)
                     FROM games
                     WHERE games.id = game_id
                       AND player_id = teams.captain_id)), 0),
       coalesce(SUM(playerGameStats.points_scored) -
                SUM((SELECT IIF(games.team_one_id = teams.id, games.team_two_score, games.team_one_score)
                     FROM games
                     WHERE games.id = game_id
                       AND player_id = teams.captain_id)), 0)
FROM teams
         INNER JOIN tournamentTeams on teams.id = tournamentTeams.team_id
         LEFT JOIN games ON (games.team_one_id = teams.id OR games.team_two_id = teams.id) AND games.is_final = 0 AND
                            games.is_bye = 0 AND (IIF(? is null, games.ranked, 1) OR teams.non_captain_id is null) AND games.tournament_id = tournamentTeams.tournament_id
         LEFT JOIN playerGameStats ON teams.id = playerGameStats.team_id AND games.id = playerGameStats.game_id
         LEFT JOIN tournaments on tournaments.id = tournamentTeams.tournament_id

where IIF(? is NULL, 1, tournaments.id = ?)
  AND teams.searchable_name = ?
;""",
                (tournament_id, tournament_id, tournament_id, team_name),
            ).fetchone()

            if not team:
                return (
                    render_template(
                        "tournament_specific/game_editor/game_done.html",
                        error="This is not a real team",
                    ),
                    400,
                )
            team = TeamStats(
                team[0],
                team[1],
                team[2],
                {k: v for k, v in zip(team_headers, team[3:])},
            )
            players = c.execute(
                """SELECT people.name,
       people.searchable_name,
       coalesce(SUM(games.best_player_id = player_id), 0),
       ROUND(1500.0 + coalesce((SELECT SUM(elo_delta)
                       from eloChange
                       where eloChange.player_id = people.id AND eloChange.game_id <= MAX(games.id)), 0), 2) as elo,
       coalesce(SUM(playerGameStats.points_scored), 0),
       coalesce(SUM(playerGameStats.aces_scored), 0),
       coalesce(SUM(playerGameStats.faults), 0),
       coalesce(SUM(playerGameStats.double_faults), 0),
       coalesce(SUM(playerGameStats.green_cards), 0),
       coalesce(SUM(playerGameStats.yellow_cards), 0),
       coalesce(SUM(playerGameStats.red_cards), 0),
       coalesce(SUM(playerGameStats.rounds_on_court), 0),
       coalesce(SUM(playerGameStats.rounds_carded), 0),
       coalesce(ROUND((SELECT SUM(elo_delta)
                       from eloChange
                                INNER JOIN games on eloChange.game_id = games.id
                       where eloChange.player_id = people.id
                         AND games.tournament_id = tournamentTeams.tournament_id), 2), 0),
       ROUND(coalesce((SELECT SUM(elo_delta)
                       from eloChange
                                INNER JOIN games on eloChange.game_id = games.id
                       where eloChange.player_id = people.id
                         AND games.tournament_id = tournamentTeams.tournament_id), 0) / COUNT(DISTINCT playerGameStats.game_id),
                2)                                               as elo,
       coalesce(SUM(playerGameStats.served_points), 0),
       ROUND(coalesce(CAST(SUM(playerGameStats.points_scored) AS REAL) / COUNT(DISTINCT playerGameStats.game_id), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.points_scored) AS REAL) / (COUNT(DISTINCT playerGameStats.game_id) -
                                                                   COUNT(DISTINCT IIF(games.winning_team_id = teams.id, games.id, NULL))),
                      0),
             2),
       ROUND(coalesce(CAST(SUM(playerGameStats.aces_scored) AS REAL) / COUNT(DISTINCT playerGameStats.game_id), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.faults) AS REAL) / COUNT(DISTINCT playerGameStats.game_id), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.green_cards + playerGameStats.yellow_cards +
                               playerGameStats.red_cards) AS REAL) /
                      COUNT(DISTINCT playerGameStats.game_id), 0), 2),
       coalesce(SUM(playerGameStats.green_cards + playerGameStats.yellow_cards + playerGameStats.red_cards), 0),
       ROUND(coalesce(CAST(SUM(playerGameStats.points_scored) AS REAL) /
                      (SUM(playerGameStats.green_cards + playerGameStats.yellow_cards + playerGameStats.red_cards)), 0),
             2),
       ROUND(coalesce(CAST(SUM(playerGameStats.served_points) AS REAL) / (COUNT(DISTINCT games.id)), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.served_points) AS REAL) / (SUM(playerGameStats.aces_scored)), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.served_points) AS REAL) / (SUM(playerGameStats.faults)), 0), 2),
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.aces_scored) AS REAL) / (SUM(playerGameStats.served_points)), 0), 2) ||
       '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.faults) AS REAL) / (SUM(playerGameStats.served_points)), 0), 2) ||
       '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.points_scored) AS REAL) /
                      (SUM(playerGameStats.rounds_on_court + playerGameStats.rounds_carded)), 0), 2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.points_scored) AS REAL) / (SUM(IIF(games.team_one_id = playerGameStats.team_id, team_one_score, team_two_score))),
                      0), 2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.start_side = 'Left') AS REAL) /
                      COUNT(DISTINCT playerGameStats.game_id), 0),
             2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.served_points_won) AS REAL) / SUM(playerGameStats.served_points),
                      0), 2) || '%',
       coalesce(SUM(playerGameStats.serves_received), 0),
       coalesce(SUM(playerGameStats.serves_returned), 0),
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.serves_returned) AS REAL) / SUM(playerGameStats.serves_received),
                      0), 2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(games.best_player_id = player_id) AS REAL) / COUNT(DISTINCT playerGameStats.game_id),
                      0), 2)


FROM teams
         INNER JOIN tournamentTeams ON teams.id = tournamentTeams.team_id
         INNER JOIN people
                    on (teams.captain_id = people.id OR teams.non_captain_id = people.id OR teams.substitute_id = people.id)
         LEFT JOIN games on (teams.id = games.team_one_id OR   teams.id = team_two_id)
          AND games.tournament_id = tournamentTeams.tournament_id and games.is_bye = 0
                                and games.is_final = 0
                                and (IIF(? is null, games.ranked, 1) or teams.non_captain_id is null)
         LEFT JOIN playerGameStats on people.id = playerGameStats.player_id AND games.id = playerGameStats.game_id
WHERE teams.searchable_name = ?

  and IIF(? is NULL, 1, tournamentTeams.tournament_id = ?)

GROUP BY people.id
ORDER BY people.id <> teams.captain_id, people.id <> teams.non_captain_id""",
                (tournament_id, team_name, tournament_id, tournament_id),
            ).fetchall()
            recent = c.execute(
                """ SELECT s.name, r.name, g1.team_one_score, g1.team_two_score, g1.id, tournaments.searchable_name
                    FROM games g1
                             INNER JOIN tournaments on g1.tournament_id = tournaments.id
                             INNER JOIN teams r on g1.team_two_id = r.id
                             INNER JOIN teams s on g1.team_one_id = s.id
                    WHERE (r.searchable_name = ? or s.searchable_name = ?) and IIF(? is NULL, 1, tournaments.id = ?) and g1.started = 1
                    ORDER BY g1.id DESC 
                    LIMIT 20""", (team_name, team_name, tournament_id, tournament_id)).fetchall()
            upcoming = c.execute(
                """ SELECT s.name, r.name, g1.team_one_score, g1.team_two_score, g1.id, tournaments.searchable_name
                    FROM games g1
                             INNER JOIN tournaments on g1.tournament_id = tournaments.id
                             INNER JOIN teams r on g1.team_two_id = r.id
                             INNER JOIN teams s on g1.team_one_id = s.id
                    WHERE (r.searchable_name = ? or s.searchable_name = ?) and tournaments.searchable_name = ? and g1.started = 0
                    ORDER BY g1.id DESC 
                    LIMIT 20""", (team_name, team_name, tournament)).fetchall()
        players = [PlayerStats(i[0], i[1], {k: v for k, v in zip(player_headers, i[2:])}) for i in players]
        recent = [
            (f"{i[0]} vs {i[1]} [{i[2]} - {i[3]}]", i[4], i[5]) for i in recent
        ]
        upcoming = [
            (f"{i[0]} vs {i[1]} [{i[2]} - {i[3]}]", i[4], i[5]) for i in upcoming
        ]
        return (
            render_template_sidebar(
                "tournament_specific/each_team_stats.html",
                stats=[(k, v) for k, v in team.stats.items()],
                team=team,
                recent_games=recent,
                upcoming_games=upcoming,
                players=players,
            ),
            200,
        )

    @app.get("/games/<game_id>/display")
    def scoreboard(game_id):
        with DatabaseManager() as c:
            players = c.execute(
                """SELECT people.name,
       people.searchable_name,
       playerGameStats.card_time,
       playerGameStats.card_time_remaining,
       playerGameStats.player_id = games.player_to_serve_id,
       coalesce(punishments.hex, '#000000'),
       coalesce((SELECT SUM(p.type == 'Green')
        FROM punishments p
        WHERE p.game_id = games.id AND p.player_id = people.id), 0),
       teams.name, -- 6
       teams.searchable_name,
       case
           when teams.image_url is null
               then '/api/teams/image?name=blank'
           else
               teams.image_url
           end,
       IIF(teams.id = games.team_one_id, games.team_one_score, games.team_two_score),
       1 - coalesce(IIF(teams.id = games.team_one_id, games.team_one_timeouts, games.team_two_timeouts), 0),
       
       games.id, --11
       po.name,
       po.searchable_name,
       ps.name,
       ps.searchable_name,
       games.court,    --16
       games.round,
       gameEvents.event_type = 'Fault',
       lastGE.side_to_serve,
       (SELECT inn.event_type
        FROM gameEvents inn
        WHERE inn.id =
              (SELECT MAX(id)
               FROM gameEvents inn2
               WHERE games.id = inn2.game_id
                 AND (inn2.notes is null or inn2.notes <> 'Penalty'))) --20
FROM games
         LEFT JOIN gameEvents lastGE ON games.id = lastGE.game_id AND lastGE.id =
                                                                     (SELECT MAX(id)
                                                                      FROM gameEvents
                                                                      WHERE games.id = gameEvents.game_id)
         LEFT JOIN playerGameStats on(lastGE.team_one_left_id = playerGameStats.player_id OR lastGE.team_one_right_id = playerGameStats.player_id OR
                                      lastGE.team_two_left_id = playerGameStats.player_id OR lastGE.team_two_right_id = playerGameStats.player_id OR lastGE.event_type is null) AND games.id = playerGameStats.game_id
         INNER JOIN tournaments on tournaments.id = games.tournament_id
         LEFT JOIN officials o on o.id = games.official_id
         LEFT JOIN people po on po.id = o.person_id
         LEFT JOIN officials s on s.id = games.scorer_id
         LEFT JOIN people ps on ps.id = s.person_id
         INNER JOIN people on people.id = playerGameStats.player_id
         LEFT JOIN people best on best.id = games.best_player_id
         INNER JOIN teams on teams.id = playerGameStats.team_id
         INNER JOIN eloChange on games.id >= eloChange.game_id and eloChange.player_id = playerGameStats.player_id
         LEFT JOIN gameEvents ON games.id = gameEvents.game_id AND gameEvents.id =
                                                                  (SELECT MAX(id)
                                                                   FROM gameEvents
                                                                   WHERE games.id = gameEvents.game_id
                                                                     AND (gameEvents.event_type = 'Fault' or gameEvents.event_type = 'Score'))

         LEFT JOIN punishments ON punishments.game_id =
                                  (SELECT MAX(id)
                                   FROM gameEvents
                                   WHERE games.id = punishments.game_id AND punishments.player_id = playerGameStats.player_id)
WHERE games.id = ?
GROUP BY people.name
order by teams.id <> games.team_one_id, (playerGameStats.player_id <> lastGE.team_one_left_id) AND (playerGameStats.player_id <> lastGE.team_two_left_id);""",
                (game_id,),
            ).fetchall()
        if not players:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="Game Does not exist",
                ),
                404,
            )

        @dataclass
        class Player:
            name: str
            searchableName: str
            cardTime: int
            cardTimeRemaining: int
            serving: bool
            hex: str
            green_carded: bool

        @dataclass
        class Team:
            players: list[Player]
            name: str
            searchableName: str
            imageUrl: str
            score: int
            timeouts: int
            cardTime: int = 0
            cardTimeRemaining: int = 0
            green_carded: bool = False

        @dataclass
        class Game:
            players: list[Player]
            teams: list[Team]
            courtName: str
            score_string: str
            id: int
            umpire: str
            umpireSearchableName: str
            scorer: str
            scorerSearchableName: str
            court: int
            round: int
            faulted: bool
            serverSide: str
            type: str

        teams = {}
        player_stats = []

        for i in players:
            pl = Player(*i[:7])
            player_stats.append(pl)
            if i[7] not in teams:
                teams[i[7]] = Team([], *i[7:12])
            teams[i[7]].players.append(pl)
            if teams[i[7]].cardTime != -1:
                if pl.cardTime and pl.cardTime < 0: teams[i[7]].cardTime = -1
                teams[i[7]].cardTime = max(pl.cardTime or 0, teams[i[7]].cardTime)
                if pl.cardTime and pl.cardTimeRemaining < 0: teams[i[7]].cardTimeRemaining = -1
                teams[i[7]].cardTimeRemaining = max(pl.cardTimeRemaining or 0, teams[i[7]].cardTimeRemaining)
                if pl.green_carded: teams[i[7]].green_carded = True
        visual_swap = request.args.get("swap", "false") == "true"
        teams = list(teams.values())
        game = Game(player_stats,
                    teams, f"Court {players[0][16]}",
                    f"{teams[0].score} - {teams[1].score}", *players[0][12:])
        if visual_swap:
            teams = list(reversed(teams))

        return (
            render_template_sidebar(
                "tournament_specific/scoreboard.html",
                game=game,
                status="Status",  # TODO: fix
                players=player_stats,
                teams=teams,
                update_count=manage_game.change_code(game_id),
                timeout_time=manage_game.get_timeout_time(game_id) * 1000,
                serve_time=manage_game.get_serve_timer(game_id) * 1000,
            ),
            200,
        )

    @app.get("/games/display")
    def court_scoreboard():
        court = int(request.args.get("court"))
        with DatabaseManager() as c:
            tournament = get_tournament_id(request.args.get("tournament"), c)
            game_id = c.execute(
                """SELECT id FROM games WHERE court = ? AND tournament_id = ? AND started = 1 ORDER BY id desc""",
                (court, tournament)).fetchone()
        return scoreboard()

    @app.get("/games/<game_id>/")
    def game_site(game_id):
        with DatabaseManager() as c:
            players = c.execute(
                """SELECT people.name,
                                       round(coalesce(SUM(eloChange.elo_delta),0) + 1500, 2) as elo,
                                       case 
                                        when round(coalesce((SELECT elo_delta
                                        from eloChange
                                        where eloChange.player_id = playerGameStats.player_id
                                          and eloChange.game_id = games.id), 0), 2) is null 
                                            then 0 
                                        else 
                                            round(coalesce((SELECT elo_delta
                                        from eloChange
                                        where eloChange.player_id = playerGameStats.player_id
                                          and eloChange.game_id = games.id), 0), 2)
                                        end as eloDelta,
                                       coalesce(playerGameStats.points_scored, 0),
                                       coalesce(playerGameStats.aces_scored, 0),
                                       coalesce(playerGameStats.faults, 0), --5
                                       coalesce(playerGameStats.double_faults, 0),
                                       coalesce(playerGameStats.rounds_on_court, 0),
                                       coalesce(playerGameStats.rounds_carded, 0),
                                       coalesce(playerGameStats.green_cards, 0),
                                       coalesce(playerGameStats.yellow_cards, 0), --10
                                       coalesce(playerGameStats.red_cards, 0),
                                       games.is_bye,   --i[12]
                                       tournaments.name,
                                       tournaments.searchable_name,
                                       teams.name, --15
                                       teams.searchable_name,
                                       games.team_one_id = teams.id,
                                       games.team_one_score,
                                       games.team_two_score,
                                       po.name, --20
                                       po.searchable_name,
                                       ps.name,
                                       ps.searchable_name,
                                       games.court,
                                       games.round,--25
                                       best.name,
                                       best.searchable_name,
                                       coalesce(games.start_time, -1),
                                       tournaments.searchable_name,
                                       teams.name, --30
                                       teams.searchable_name,
                                       case 
                                        when teams.image_url is null 
                                            then '/api/teams/image?name=blank' 
                                        else 
                                            teams.image_url
                                        end,
                                       people.searchable_name,
                                       games.status,
                                       games.team_one_timeouts,
                                       games.team_two_timeouts
                
                                FROM games
                                         LEFT JOIN playerGameStats on playerGameStats.game_id = games.id
                                         INNER JOIN tournaments on tournaments.id = games.tournament_id
                                         LEFT JOIN officials o on o.id = games.official_id
                                         LEFT JOIN people po on po.id = o.person_id
                                         LEFT JOIN officials s on s.id = games.scorer_id
                                         LEFT JOIN people ps on ps.id = s.person_id
                                         LEFT JOIN people on people.id = playerGameStats.player_id
                                         LEFT JOIN people best on best.id = games.best_player_id
                                         LEFT JOIN teams on teams.id = playerGameStats.team_id
                                         LEFT JOIN eloChange on games.id > eloChange.game_id and eloChange.player_id = playerGameStats.player_id
                                         LEFT JOIN gameEvents on gameEvents.id = (SELECT MAX(id) FROM gameEvents WHERE games.id = gameEvents.game_id)
                                WHERE games.id = ?
                                GROUP BY people.name
                                order by teams.id <> games.team_one_id, (playerGameStats.player_id = team_one_left_id OR playerGameStats.player_id = team_two_left_id) DESC;""",
                (game_id,),
            ).fetchall()

            other_matches = c.execute(
                """ SELECT s.name, r.name, g2.team_one_score, g2.team_two_score, g2.id, tournaments.searchable_name
                    FROM games g1
                             INNER JOIN games g2
                                        ON ((g2.team_one_id = g1.team_one_id AND g2.team_two_id = g1.team_two_id)
                                            OR (g2.team_one_id = g1.team_two_id AND g2.team_two_id = g1.team_one_id))
                                            AND g1.id <> g2.id --funny != symbol lol
                             INNER JOIN tournaments on g2.tournament_id = tournaments.id
                             INNER JOIN teams r on g2.team_two_id = r.id
                             INNER JOIN teams s on g2.team_one_id = s.id
                    WHERE g1.id = ?
                    ORDER BY g2.id DESC 
                    LIMIT 20""",
                (game_id,),
            ).fetchall()
        if not players:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="Game Does not exist",
                ),
                404,
            )

        @dataclass
        class Player:
            name: str
            searchableName: str
            stats: dict[str, any]
            elo: float
            elo_delta: float

        player_headers = [
            "ELO",
            "Points Scored",
            "Aces",
            "Faults",
            "Double Faults",
            "Rounds Played",
            "Rounds Benched",
            "Green Cards",
            "Yellow Cards",
            "Red Cards",
        ]

        team_headers = [
            "Elo",
            "Green Cards",
            "Yellow Cards",
            "Red Cards",
            "Timeouts Remaining",
        ]

        def make_player(row):
            name = row[0]
            elo = row[1]
            elo_delta = row[2]
            stats = [f"{row[1]} [{(row[2]) if row[2] < 0 else '+' + str(row[2])}]"]
            stats += list(row[3:12])
            return Player(
                name,
                row[33],
                {k: v for k, v in zip(player_headers, stats)},
                elo,
                elo_delta,
            )

        @dataclass
        class Team:
            players: list[Player]
            image: str
            name: str
            searchableName: str
            stats: dict[str, any]
            elo: int = 0
            timeouts: int = 0

        @dataclass
        class Game:
            players: list[Player]
            teams: list[Team]
            score_string: str
            id: int
            umpire: str
            umpireSearchableName: str
            scorer: str
            scorerSearchableName: str
            court: int
            round: int
            courtName: str
            bye: bool
            bestName: str
            bestSearchableName: str
            startTime: float
            startTimeStr: str
            status: str

        player_stats = []
        teams = {}
        for i in players:
            pl = make_player(i)
            player_stats.append(pl)
            if i[30] not in teams:
                teams[i[30]] = Team([], i[32] if i[32] else "", i[30], i[31], {})
            teams[i[30]].players.append(pl)
            teams[i[30]].stats["Green Cards"] = (
                    teams[i[30]].stats.get("Green Cards", 0) + i[9]
            )
            teams[i[30]].stats["Yellow Cards"] = (
                    teams[i[30]].stats.get("Yellow Cards", 0) + i[10]
            )
            teams[i[30]].stats["Red Cards"] = (
                    teams[i[30]].stats.get("Red Cards", 0) + i[11]
            )
        for i, team in enumerate(teams.values()):
            if i:
                team.stats["Timeouts Remaining"] = 1 - players[0][36]
            else:
                team.stats["Timeouts Remaining"] = 1 - players[0][35]

        for i in teams.values():
            i.elo = round(sum(j.elo for j in i.players) / len(i.players), 2)
            i.elo_delta = round(sum(j.elo_delta for j in i.players) / len(i.players), 2)
            i.stats[
                "Elo"
            ] = f"{i.elo} [{i.elo_delta if i.elo_delta < 0 else '+' + str(i.elo_delta)}]"

        teams = list(teams.values())
        time_float = float(players[0][28])

        game = Game(
            player_stats,
            teams,
            f"{players[0][18]} - {players[0][19]}",
            game_id,
            players[0][20],
            players[0][21],
            players[0][22],
            players[0][23],
            players[0][24],
            players[0][25],
            f"Court {players[0][24] + 1}",
            players[0][12],
            players[0][26],
            players[0][27],
            players[0][28],
            "?"
            if time_float < 0
            else time.strftime("%d/%m/%y (%H:%M)", time.localtime(time_float)),
            players[0][34],
        )

        best = game.bestSearchableName if game.bestSearchableName else "TBD"

        round_number = game.round
        prev_matches = [
            (f"{i[0]} vs {i[1]} [{i[2]} - {i[3]}]", i[4], i[5]) for i in other_matches
        ]
        prev_matches = prev_matches or [("No other matches", -1, players[0][29])]
        return (
            render_template_sidebar(
                "tournament_specific/game_page.html",
                game=game,
                teams=teams,
                best=best,
                team_headings=team_headers,
                player_headings=player_headers,
                commentary=game_string_to_commentary(game.id),
                roundNumber=round_number,
                prev_matches=prev_matches,
                tournament=players[0][13],
                tournamentLink=players[0][14] + "/",
            ),
            200,
        )

    @app.get("/<tournament>/ladder/")
    def ladder_site(tournament):
        priority = {
            "Team Names": 1,
            "Games Played": 2,
            "Games Won": 1,
            "Percentage": 1,
            "Games Lost": 3,
            "Green Cards": 5,
            "Yellow Cards": 4,
            "Red Cards": 4,
            "Faults": 5,
            "Timeouts Called": 5,
            "Points For": 5,
            "Points Against": 5,
            "Point Difference": 2,
            "Elo": 3,
        }

        @dataclass
        class Team:
            name: str
            searchableName: str
            pool: int
            image: str
            stats: dict[str, object]

        with DatabaseManager() as c:
            tournament_id = get_tournament_id(tournament, c)
            teams = c.execute(
                """SELECT tournaments.is_pooled,
       teams.searchable_name,
       teams.name,
       case
           when teams.image_url is null
               then '/api/teams/image?name=blank'
           else
               teams.image_url
           end,
       tournamentTeams.pool,
       COUNT(DISTINCT IIF(g.someone_has_won, g.id, null)) as played,
       SUM(IIF(playerGameStats.player_id = teams.captain_id, teams.id = g.winning_team_id,
               0))                                      as wins,
       ROUND(100.0 * coalesce(
               Cast(SUM(IIF(playerGameStats.player_id = teams.captain_id, teams.id = g.winning_team_id, 0)) AS REAL) /
               COUNT(DISTINCT IIF(g.someone_has_won, g.id, null)), 0),
             2) ||
       '%'                                              as percentage,
       COUNT(DISTINCT IIF(g.someone_has_won, g.id, null)) - SUM(IIF(playerGameStats.player_id = teams.captain_id, teams.id = g.winning_team_id,
                                      0))               as losses,
       coalesce(SUM(playerGameStats.green_cards), 0)     as green_cards,
       coalesce(SUM(playerGameStats.yellow_cards), 0)    as yellow_cards,
       coalesce(SUM(playerGameStats.red_cards), 0)       as red_cards,
       coalesce(SUM(playerGameStats.faults), 0)         as faults,
       SUM(IIF(playerGameStats.player_id = teams.captain_id,
               IIF(g.team_one_id = teams.id, team_one_timeouts, team_two_timeouts), 0)),
       coalesce(SUM(playerGameStats.points_scored), 0)         as pointsScored,
       coalesce((SELECT SUM(playerGameStats.points_scored)
                 FROM playerGameStats
                 where playerGameStats.opponent_id = teams.id
                   and playerGameStats.tournament_id = tournaments.id),
                0)                                      as pointsConceded,
       coalesce(SUM(playerGameStats.points_scored) - (SELECT SUM(playerGameStats.points_scored)
                                               FROM playerGameStats
                                               where playerGameStats.opponent_id = teams.id
                                                 and playerGameStats.tournament_id = tournaments.id),
                0)                                      as difference,
       ROUND(1500.0 + coalesce((SELECT SUM(elo_delta)
                                from eloChange
                                         INNER JOIN teams inside ON inside.id = teams.id
                                         INNER JOIN people captain ON captain.id = inside.captain_id
                                         LEFT JOIN people non_captain ON non_captain.id = inside.non_captain_id
                                         LEFT JOIN people sub ON sub.id = inside.substitute_id
                                where eloChange.player_id = sub.id
                                   or eloChange.player_id = captain.id
                                   or eloChange.player_id = non_captain.id AND eloChange.game_id <=MAX(g.id)),
                               0)
           /
                      COUNT(teams.captain_id is not null + teams.non_captain_id is not null + teams.substitute_id is not null),
             2)                                         as elo

FROM teams
         INNER JOIN tournamentTeams on teams.id = tournamentTeams.team_id
         LEFT JOIN games g ON (g.team_one_id = teams.id OR g.team_two_id = teams.id) AND g.is_final = 0 AND
                              g.is_bye = 0 AND (IIF(? is null, g.ranked, 1) OR teams.non_captain_id is null) AND
                              g.tournament_id = tournamentTeams.tournament_id
         LEFT JOIN playerGameStats ON teams.id = playerGameStats.team_id AND g.id = playerGameStats.game_id
         LEFT JOIN tournaments on tournaments.id = tournamentTeams.tournament_id

where IIF(? is NULL, 1, tournaments.id = ?)
GROUP BY teams.name
ORDER BY Cast(SUM(IIF(playerGameStats.player_id = teams.captain_id, teams.id = g.winning_team_id, 0)) AS REAL) /
         COUNT(DISTINCT g.id) DESC,
         difference DESC,
         pointsScored DESC,
         green_cards + yellow_cards + red_cards ASC,
         red_cards ASC,
         yellow_cards ASC,
         faults ASC,
         SUM(IIF(team_one_id = teams.id, team_one_timeouts, team_two_timeouts)) ASC""",
                (tournament_id, tournament_id, tournament_id),
            ).fetchall()
        ladder = [
            Team(i[2], i[1], i[4], i[3], {k: v for k, v in zip(priority, i[5:])})
            for i in teams
        ]
        if teams[0][0]:  # this tournament is pooled
            ladder = [
                (
                    f"Pool {numbers[i]}",
                    i,
                    list(enumerate((j for j in ladder if j.pool == i), start=1)),
                )
                for i in range(1, 3)
            ]
        else:
            ladder = [("", 0, list(enumerate(ladder, start=1)))]
        headers = [
            (i, priority_to_classname(priority[i])) for i in ([i for i in priority])
        ]
        return (
            render_template_sidebar(
                "tournament_specific/ladder.html",
                headers=[(i - 1, k, v) for i, (k, v) in enumerate(headers)],
                priority={k: priority_to_classname(v) for k, v in priority.items()},
                ladder=ladder,
            ),
            200,
        )

    @app.get("/<tournament>/players/")
    def players_site(tournament):
        priority = {
            "Name": 1,
            "B&F Votes": 1,
            "Elo": 1,
            "Points Scored": 2,
            "Aces Scored": 2,
            "Faults": 5,
            "Double Faults": 5,
            "Green Cards": 4,
            "Yellow Cards": 3,
            "Red Cards": 3,
            "Rounds Played": 5,
            "Points Served": 5,
            "Rounds Carded": 5,
            "Games Played": 5,
            "Games Won": 4,
        }
        player_headers = ["Name",
                          "B&F Votes",
                          "Elo",
                          "Games Won",
                          "Games Played",
                          "Points Scored",
                          "Aces Scored",
                          "Faults",
                          "Double Faults",
                          "Green Cards",
                          "Yellow Cards",
                          "Red Cards",
                          "Rounds Played",
                          "Points Served",
                          ]
        tournament_id = get_tournament_id(tournament)
        # TODO (LACHIE): please help me make this less queries...
        with DatabaseManager() as c:
            players_query = c.execute(
                """SELECT coalesce(min(teams.image_url) FILTER ( WHERE teams.image_url Like '/api/teams/image?%'),teams.image_url),
       people.searchable_name,
       people.name,
       coalesce(SUM(games.best_player_id = player_id), 0),
       ROUND(1500.0 + coalesce((SELECT SUM(elo_delta)
                       from eloChange
                       where eloChange.player_id = people.id AND eloChange.game_id <= MAX(games.id)), 0), 2)  as elo,
       coalesce(SUM(games.winning_team_id = playerGameStats.team_id), 0),
       COUNT(DISTINCT games.id),
       coalesce(SUM(playerGameStats.points_scored), 0),
       coalesce(SUM(playerGameStats.aces_scored), 0),
       coalesce(SUM(playerGameStats.faults), 0),
       coalesce(SUM(playerGameStats.double_faults), 0),
       coalesce(SUM(playerGameStats.green_cards), 0),
       coalesce(SUM(playerGameStats.yellow_cards), 0),
       coalesce(SUM(playerGameStats.red_cards), 0),
       coalesce(SUM(playerGameStats.rounds_on_court), 0),
       coalesce(SUM(playerGameStats.served_points), 0)

FROM tournamentTeams
         INNER JOIN teams ON teams.id = tournamentTeams.team_id
         INNER JOIN people
                    ON (people.id = teams.captain_id OR people.id = teams.non_captain_id OR teams.substitute_id = people.id)
         INNER JOIN tournaments on tournaments.id = tournamentTeams.tournament_id
         LEFT JOIN games
                   on (teams.id = games.team_one_id OR teams.id = team_two_id)  AND games.is_bye = 0 and games.is_final = 0 and IIF(? is NULL, games.ranked, 1) and
                      tournaments.id = games.tournament_id
         LEFT JOIN playerGameStats on games.id = playerGameStats.game_id AND player_id = people.id
         
WHERE IIF(? is NULL, 1, tournaments.id = ?)
GROUP BY people.id""",
                (tournament_id, tournament_id, tournament_id), ).fetchall()

        players = []
        # Im so fucking lazy so im not gonna use a dataclass.  Fucking fight me idec
        for i in players_query:
            players.append(
                (i[2], i[0], i[1], [(v, (priority_to_classname(priority[k]))) for k, v in zip(player_headers, i[3:])]))
        print(players[1])
        return (
            render_template_sidebar(
                "tournament_specific/players.html",
                headers=[
                    (i - 1, k, priority_to_classname(priority[k]))
                    for i, k in enumerate(player_headers)
                ],
                players=sorted(players, key=lambda a: a[3][1][0]),
            ),
            200,
        )

    @app.get("/<tournament>/players/detailed")
    def detailed_players_site(tournament):
        players = People.query.all()
        game_filter = (lambda a: a.filter(PlayerGameStats.tournament_id == tournament)) if tournament else None
        players = [(i, i.stats(games_filter=game_filter)) for i in players]
        return (
            render_template_sidebar(
                "tournament_specific/players_detailed.html",
                headers=[(i - 1, k) for i, k in enumerate(["Name"] + players[0][1].keys())],
                players=players,
                tournament=link(tournament),
            ),
            200,
        )

    @app.get("/<tournament>/players/<player_name>/")
    def player_stats(tournament, player_name):
        tournament_id = get_tournament_id(tournament)
        player_headers = ["B&F Votes",
                          "Elo",
                          "Games Won",
                          "Games Lost",
                          "Games Played",
                          "Percentage",
                          "Points scored",
                          "Aces scored",
                          "Faults",
                          "Double Faults",
                          "Green Cards",
                          "Yellow Cards",
                          "Red Cards",
                          "Rounds on Court",
                          "Rounds on Bench",
                          "Net Elo Delta",
                          "Average Elo Delta",
                          "Points served",
                          "Points Per Game",  # ppg
                          "Points Per Loss",
                          "Aces Per Game",
                          "Faults Per Game",
                          "Cards Per Game",
                          "Cards",
                          "Points Per Card",
                          "Serves Per Game",
                          "Serves Per Ace",
                          "Serves Per Fault",
                          "Serve Ace Rate",
                          "Serve Fault Rate",
                          "Percentage of Points scored",
                          "Percentage of Points scored for Team",
                          "Percentage of Games as Left Player",
                          "Serving Conversion Rate",
                          # "Average Serving Streak",
                          # "Max. Serving Streak",
                          # "Max. Ace Streak",
                          "Serves Received",
                          "Serves Returned",
                          "Return Rate",
                          "Votes Per 100 Games"]
        # TODO (LACHIE): please help me make this less queries...
        with DatabaseManager() as c:
            players = c.execute(
                """SELECT people.name,
       coalesce(min(teams.searchable_name) FILTER ( WHERE teams.image_url Like '/api/teams/image?%'),teams.searchable_name),
       coalesce(min(teams.image_url) FILTER ( WHERE teams.image_url Like '/api/teams/image?%'),teams.image_url),
       coalesce(SUM(best_player_id = player_id), 0),
       ROUND(1500.0 + coalesce((SELECT SUM(elo_delta)
                       from eloChange
                       where eloChange.player_id = people.id AND eloChange.game_id <= MAX(games.id)), 0), 2) ,
       coalesce(SUM(winning_team_id = teams.id), 0),
       coalesce(SUM(winning_team_id <> teams.id), 0),
       COUNT(DISTINCT games.id),
       ROUND(coalesce(100.0 * CAST(SUM(winning_team_id = teams.id)  AS REAL) / COUNT(DISTINCT games.id), 0), 2) || '%',
       coalesce(SUM(playerGameStats.points_scored), 0),
       coalesce(SUM(playerGameStats.aces_scored), 0),
       coalesce(SUM(playerGameStats.faults), 0),
       coalesce(SUM(playerGameStats.double_faults), 0),
       coalesce(SUM(playerGameStats.green_cards), 0),
       coalesce(SUM(playerGameStats.yellow_cards), 0),
       coalesce(SUM(playerGameStats.red_cards), 0),
       coalesce(SUM(playerGameStats.rounds_on_court), 0),
       coalesce(SUM(playerGameStats.rounds_carded), 0),
       coalesce(ROUND((SELECT SUM(elo_delta)
                       from eloChange
                                INNER JOIN games on eloChange.game_id = games.id
                       where eloChange.player_id = people.id
                         AND games.tournament_id = tournamentTeams.tournament_id), 2), 0),
       ROUND(coalesce((SELECT SUM(elo_delta)
                       from eloChange
                                INNER JOIN games on eloChange.game_id = games.id
                       where eloChange.player_id = people.id
                         AND games.tournament_id = tournamentTeams.tournament_id), 0) / COUNT(DISTINCT playerGameStats.game_id),
             2)                                               as elo,
       coalesce(SUM(playerGameStats.served_points), 0),
       ROUND(coalesce(CAST(SUM(playerGameStats.points_scored) AS REAL) / COUNT(DISTINCT playerGameStats.game_id), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.points_scored) AS REAL) / (COUNT(DISTINCT playerGameStats.game_id) -
                                                                   COUNT(DISTINCT IIF(games.winning_team_id = teams.id, games.id, NULL))),
                      0),
             2),
       ROUND(coalesce(CAST(SUM(playerGameStats.aces_scored) AS REAL) / COUNT(DISTINCT playerGameStats.game_id), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.faults) AS REAL) / COUNT(DISTINCT playerGameStats.game_id), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.green_cards + playerGameStats.yellow_cards +
                               playerGameStats.red_cards) AS REAL) /
                      COUNT(DISTINCT playerGameStats.game_id), 0), 2),
       coalesce(SUM(playerGameStats.green_cards + playerGameStats.yellow_cards + playerGameStats.red_cards), 0),
       ROUND(coalesce(CAST(SUM(playerGameStats.points_scored) AS REAL) /
                      (SUM(playerGameStats.green_cards + playerGameStats.yellow_cards + playerGameStats.red_cards)), 0),
             2),
       ROUND(coalesce(CAST(SUM(playerGameStats.served_points) AS REAL) / (COUNT(DISTINCT games.id)), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.served_points) AS REAL) / (SUM(playerGameStats.aces_scored)), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.served_points) AS REAL) / (SUM(playerGameStats.faults)), 0), 2),
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.aces_scored) AS REAL) / (SUM(playerGameStats.served_points)), 0), 2) ||
       '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.faults) AS REAL) / (SUM(playerGameStats.served_points)), 0), 2) ||
       '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.points_scored) AS REAL) /
                      (SUM(playerGameStats.rounds_on_court + playerGameStats.rounds_carded)), 0), 2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.points_scored) AS REAL) / (SUM(IIF(games.team_one_id = playerGameStats.team_id, team_one_score, team_two_score))),
                      0), 2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.start_side = 'Left') AS REAL) /
                      COUNT(DISTINCT playerGameStats.game_id), 0),
             2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.served_points_won) AS REAL) / SUM(playerGameStats.served_points),
                      0), 2) || '%',
       coalesce(SUM(playerGameStats.serves_received), 0),
       coalesce(SUM(playerGameStats.serves_returned), 0),
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.serves_returned) AS REAL) / SUM(playerGameStats.serves_received),
                      0), 2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(best_player_id = player_id) AS REAL) / COUNT(DISTINCT playerGameStats.game_id),
                      0), 2)


FROM teams
         INNER JOIN tournamentTeams ON teams.id = tournamentTeams.team_id
         INNER JOIN people
                    on (teams.captain_id = people.id OR teams.non_captain_id = people.id OR teams.substitute_id = people.id)
         LEFT JOIN games on (teams.id = games.team_one_id OR teams.id = team_two_id)
    AND games.tournament_id = tournamentTeams.tournament_id and games.is_bye = 0
    and games.is_final = 0
    and (IIf(? is null, games.ranked, 1) or teams.non_captain_id is null)
         LEFT JOIN playerGameStats on people.id = playerGameStats.player_id AND games.id = playerGameStats.game_id
WHERE people.searchable_name = ?

  and IIF(? is NULL, 1, tournamentTeams.tournament_id = ?)
  ORDER BY teams.image_url LIKE '/api/teams/image?%'""",
                (tournament_id, player_name, tournament_id, tournament_id), ).fetchone()

            courts = c.execute(
                """SELECT people.name,
       teams.searchable_name,
       coalesce(SUM(best_player_id = player_id), 0),
       ROUND(1500.0 + (SELECT SUM(elo_delta)
                       from eloChange
                       where eloChange.player_id = people.id AND eloChange.game_id <= MAX(games.id))) as elo,
       coalesce(SUM(winning_team_id = teams.id), 0),
       coalesce(SUM(winning_team_id <> teams.id), 0),
       COUNT(DISTINCT games.id),
       ROUND(coalesce(100.0 * CAST(SUM(winning_team_id = teams.id)  AS REAL) / COUNT(DISTINCT games.id), 0), 2) || '%',
       coalesce(SUM(playerGameStats.points_scored), 0),
       coalesce(SUM(playerGameStats.aces_scored), 0),
       coalesce(SUM(playerGameStats.faults), 0),
       coalesce(SUM(playerGameStats.double_faults), 0),
       coalesce(SUM(playerGameStats.green_cards), 0),
       coalesce(SUM(playerGameStats.yellow_cards), 0),
       coalesce(SUM(playerGameStats.red_cards), 0),
       coalesce(SUM(playerGameStats.rounds_on_court), 0),
       coalesce(SUM(playerGameStats.rounds_carded), 0),
       coalesce(ROUND((SELECT SUM(elo_delta)
                       from eloChange
                                INNER JOIN games on eloChange.game_id = games.id
                       where eloChange.player_id = people.id
                         AND games.tournament_id = tournamentTeams.tournament_id), 2), 0),
       ROUND(coalesce((SELECT SUM(elo_delta)
                       from eloChange
                                INNER JOIN games on eloChange.game_id = games.id
                       where eloChange.player_id = people.id
                         AND games.tournament_id = tournamentTeams.tournament_id), 0) / COUNT(DISTINCT playerGameStats.game_id),
             2)                                               as elo,
       coalesce(SUM(playerGameStats.served_points), 0),
       ROUND(coalesce(CAST(SUM(playerGameStats.points_scored) AS REAL) / COUNT(DISTINCT playerGameStats.game_id), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.points_scored) AS REAL) / (COUNT(DISTINCT playerGameStats.game_id) -
                                                                   COUNT(DISTINCT IIF(games.winning_team_id = teams.id, games.id, NULL))),
                      0),
             2),
       ROUND(coalesce(CAST(SUM(playerGameStats.aces_scored) AS REAL) / COUNT(DISTINCT playerGameStats.game_id), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.faults) AS REAL) / COUNT(DISTINCT playerGameStats.game_id), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.green_cards + playerGameStats.yellow_cards +
                               playerGameStats.red_cards) AS REAL) /
                      COUNT(DISTINCT playerGameStats.game_id), 0), 2),
       coalesce(SUM(playerGameStats.green_cards + playerGameStats.yellow_cards + playerGameStats.red_cards), 0),
       ROUND(coalesce(CAST(SUM(playerGameStats.points_scored) AS REAL) /
                      (SUM(playerGameStats.green_cards + playerGameStats.yellow_cards + playerGameStats.red_cards)), 0),
             2),
       ROUND(coalesce(CAST(SUM(playerGameStats.served_points) AS REAL) / (SUM(playerGameStats.aces_scored)), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.served_points) AS REAL) / (SUM(playerGameStats.faults)), 0), 2),
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.aces_scored) AS REAL) / (SUM(playerGameStats.served_points)), 0), 2) ||
       '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.faults) AS REAL) / (SUM(playerGameStats.served_points)), 0), 2) ||
       '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.points_scored) AS REAL) /
                      (SUM(playerGameStats.rounds_on_court + playerGameStats.rounds_carded)), 0), 2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.points_scored) AS REAL) / (SUM(IIF(games.team_one_id = playerGameStats.team_id, team_one_score, team_two_score))),
                      0), 2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.start_side = 'Left') AS REAL) /
                      COUNT(DISTINCT playerGameStats.game_id), 0),
             2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.served_points_won) AS REAL) / SUM(playerGameStats.served_points),
                      0), 2) || '%',
       coalesce(SUM(playerGameStats.serves_received), 0),
       coalesce(SUM(playerGameStats.serves_returned), 0),
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.serves_returned) AS REAL) / SUM(playerGameStats.serves_received),
                      0), 2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(best_player_id = player_id) AS REAL) / COUNT(DISTINCT playerGameStats.game_id),
                      0), 2)


FROM teams
         INNER JOIN tournamentTeams ON teams.id = tournamentTeams.team_id
         INNER JOIN people
                    on (teams.captain_id = people.id OR teams.non_captain_id = people.id OR teams.substitute_id = people.id)
         LEFT JOIN games on (teams.id = games.team_one_id OR teams.id = team_two_id)
    AND games.tournament_id = tournamentTeams.tournament_id and games.is_bye = 0
    and games.is_final = 0
    and (IIf(? is null, games.ranked, 1) or teams.non_captain_id is null)
         LEFT JOIN playerGameStats on people.id = playerGameStats.player_id AND games.id = playerGameStats.game_id
WHERE people.searchable_name = ?

  and IIF(? is NULL, 1, tournamentTeams.tournament_id = ?) AND court >= 0
  group by games.court""",
                (tournament_id, player_name, tournament_id, tournament_id)).fetchall()

            recent = c.execute(
                """ SELECT s.name, r.name, g1.team_one_score, g1.team_two_score, g1.id, tournaments.searchable_name, 
                round(coalesce(elo_delta, 0), 2)
                    FROM games g1
                             INNER JOIN tournaments on g1.tournament_id = tournaments.id
                             INNER JOIN teams r on g1.team_two_id = r.id
                             INNER JOIN teams s on g1.team_one_id = s.id
                             INNER JOIN playerGameStats on g1.id = playerGameStats.game_id
                             INNER JOIN people on playerGameStats.player_id = people.id
                             LEFT JOIN eloChange on eloChange.game_id = g1.id AND eloChange.player_id = people.id
                    WHERE (people.searchable_name = ?) and IIF(? is NULL, 1, tournaments.id = ?) and g1.started = 1
                    ORDER BY g1.id DESC 
                    LIMIT 20""", (player_name, tournament_id, tournament_id)).fetchall()
            upcoming = c.execute(
                """ SELECT s.name, r.name, g1.team_one_score, g1.team_two_score, g1.id, tournaments.searchable_name
                    FROM games g1
                             INNER JOIN tournaments on g1.tournament_id = tournaments.id
                             INNER JOIN teams r on g1.team_two_id = r.id
                             INNER JOIN teams s on g1.team_one_id = s.id
                             INNER JOIN playerGameStats on g1.id = playerGameStats.game_id
                             INNER JOIN people on playerGameStats.player_id = people.id
                    WHERE people.searchable_name = ? and IIF(? is NULL, 1, tournaments.id = ?) and g1.started = 0 and g1.is_bye = 0
                    ORDER BY g1.id DESC 
                    LIMIT 20""", (player_name, tournament_id, tournament_id)).fetchall()
        if not players:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This is not a real player",
                ),
                400,
            )
        recent = [
            (f"{i[0]} vs {i[1]} [{i[2]} - {i[3]}] <{'' if i[6] < 0 else '+'}{i[6]}>", i[4], i[5]) for i in recent
        ]
        upcoming = [
            (f"{i[0]} vs {i[1]} [{i[2]} - {i[3]}]", i[4], i[5]) for i in upcoming
        ]

        stats = {}
        for k, v in zip(player_headers, players[3:]):
            stats[k] = v
        stats |= {
            f"Court {i + 1}": {k: v for k, v in zip(player_headers, j[2:])} for i, j in enumerate(courts)
        }

        if user_on_mobile():
            return (
                render_template_sidebar(
                    "tournament_specific/player_stats.html",
                    stats=stats,
                    name=players[0],
                    player=player_name,
                    team=players[1],
                    team_image=players[2],
                    recent_games=recent,
                    upcoming_games=upcoming,
                ),
                200,
            )
        else:
            return (
                render_template_sidebar(
                    "tournament_specific/new_player_stats.html",
                    stats=stats,
                    name=players[0],
                    player=player_name,
                    team=players[1],
                    recent_games=recent,
                    upcoming_games=upcoming,
                    insights=sorted(list(set(PlayerGameStats.rows.keys()) | set(Games.row_titles)))
                ),
                200,
            )

    @app.get("/<tournament>/officials/<nice_name>/")
    def official_site(tournament, nice_name):

        recent_games = []
        titles = [
            "Green Cards Given",
            "Yellow Cards Given",
            "Red Cards Given",
            "Cards Given",
            "Cards Per Game",
            "Faults Called",
            "Faults Per Game",
            "Games Umpired",
            "Games Scored",
            "Rounds Umpired",
        ]
        tournament_id = get_tournament_id(tournament)
        with DatabaseManager() as c:
            values = c.execute(
                """SELECT
                                   people.name,
                                   SUM(punishments.type = 'Green'),
                                   SUM(punishments.type = 'Yellow'),
                                   SUM(punishments.type = 'Red'),
                                   COUNT(punishments.reason),
                                   ROUND(CAST(COUNT(punishments.reason) AS REAL) / COUNT(DISTINCT games.id), 2),
                                   (SELECT SUM(faults)
                                    FROM games
                                             INNER JOIN playerGameStats on games.id = playerGameStats.game_id
                                    WHERE games.official_id = officials.id),
                                   ROUND(CAST((SELECT SUM(faults)
                                         FROM games
                                                  INNER JOIN playerGameStats on games.id = playerGameStats.game_id
                                         WHERE games.official_id = officials.id) AS REAL) / COUNT(DISTINCT games.id), 2),
                                   COUNT(DISTINCT games.id),
                                   COUNT((SELECT games.id FROM games WHERE games.scorer_id = officials.id)),
                                   SUM((SELECT team_one_score + team_two_score FROM games WHERE games.official_id = officials.id))
                            
                                    FROM officials
                                             INNER JOIN people on people.id = officials.person_id
                                             INNER JOIN games on games.official_id = officials.id
                                             LEFT JOIN punishments on games.id = punishments.game_id
                                             INNER JOIN tournaments ON tournaments.id = games.tournament_id
                                    WHERE people.searchable_name = ? and IIF(? is NULL, 1, tournaments.id = ?)
            """,
                (nice_name, tournament_id, tournament_id,),
            ).fetchone()
            games = c.execute(
                """SELECT DISTINCT games.id,
                tournaments.searchable_name,
                po.searchable_name = ?,
                round,
                st.name,
                rt.name,
                team_one_score,
                team_two_score
            FROM games
                     INNER JOIN officials o on games.official_id = o.id
                     INNER JOIN tournaments on games.tournament_id = tournaments.id
                     LEFT JOIN teams st on st.id = games.team_one_id
                     LEFT JOIN teams rt on rt.id = games.team_two_id
                     LEFT JOIN officials s on games.scorer_id = s.id
                     LEFT JOIN main.people po on po.id = o.person_id
                     LEFT JOIN main.people ps on ps.id = s.person_id
            WHERE (po.searchable_name = ? or ps.searchable_name = ?) AND IIF(? is NULL, 1, tournaments.id = ?) 
            ORDER BY games.id;
            """,
                (nice_name, nice_name, nice_name, tournament_id, tournament_id),
            ).fetchall()
        for (
                game_id,
                tournament_nice_name,
                umpire,
                game_round,
                team_one,
                team_two,
                score_one,
                score_two,
        ) in games:
            recent_games.append(
                (
                    f"{'Umpire ' if umpire else 'Scorer'} Round {game_round + 1}: {team_one} - {team_two} ({score_one} - {score_two})",
                    game_id,
                    tournament_nice_name,
                )
            )

        return (
            render_template_sidebar(
                "tournament_specific/official.html",
                name=values[0],
                link=nice_name,
                stats=zip(titles, values[1:]),
                games=recent_games,
            ),
            200,
        )

    @app.get("/<tournament>/officials/")
    def official_directory_site(tournament):
        tournament_id = get_tournament_id(tournament)
        with DatabaseManager() as c:
            official = c.execute(
                """
            SELECT name, searchable_name from officials INNER JOIN people on people.id = officials.person_id INNER JOIN tournamentOfficials ON officials.id = tournamentOfficials.official_id 
            WHERE IIF(? is NULL, 1, tournamentOfficials.tournament_id = ?)""", (tournament_id, tournament_id)
            ).fetchall()
        return (

            render_template_sidebar(
                "tournament_specific/all_officials.html",
                officials=official,
            ),
            200,
        )

    @app.get("/games/<game_id>/edit/")
    @officials_only
    def game_editor(game_id):
        visual_swap = request.args.get("swap", "false") == "true"
        visual_str = "true" if visual_swap else "false"

        with DatabaseManager() as c:
            game_query = c.execute("""
SELECT games.tournament_id,
      tournaments.fixtures_type,
       is_bye,
       po.name,
       po.searchable_name,
       ps.name,
       ps.searchable_name,
       started,
       someone_has_won,
       tournaments.image_url,
       gameEvents.event_type = 'Fault',
       server.name,
       lastGe.side_to_serve,
       ended,
       tournaments.has_scorer,
       team_one_score + team_two_score
FROM games
         INNER JOIN tournaments ON games.tournament_id = tournaments.id
         LEFT JOIN officials o ON games.official_id = o.id
         LEFT JOIN people po ON o.person_id = po.id
         LEFT JOIN officials s ON games.scorer_id = o.id
         LEFT JOIN people ps ON s.person_id = ps.id
         LEFT JOIN gameEvents ON games.id = gameEvents.game_id AND gameEvents.id =
                                                                  (SELECT MAX(id)
                                                                   FROM gameEvents
                                                                   WHERE games.id = gameEvents.game_id
                                                                     AND (gameEvents.event_type = 'Fault' or gameEvents.event_type = 'Score'))
         LEFT JOIN gameEvents lastGE ON games.id = lastGE.game_id AND lastGE.id =
                                                                     (SELECT MAX(id)
                                                                      FROM gameEvents
                                                                      WHERE games.id = gameEvents.game_id)
         LEFT JOIN people server on lastGE.player_to_serve_id = server.id
WHERE games.id = ?
            """, (game_id,)).fetchone()

            teams_query = c.execute("""SELECT teams.id, teams.name,
       teams.searchable_name,
       teams.id <> games.team_one_id,
       Case
           WHEN games.team_two_id = teams.id THEN
               games.team_two_score
           ELSE
               games.team_one_score END,
       case
           when teams.image_url is null
               then '/api/teams/image?name=blank'
           else
               teams.image_url
           end,
        teams.id = games.team_to_serve_id,
        IIF(sum(playerGameStats.red_cards) > 0, -1, max(playerGameStats.card_time_remaining)),
        max(IIF(playerGameStats.card_time is null, 0, playerGameStats.card_time)),
        max(playerGameStats.green_cards) > 0,
        Case
           WHEN games.team_two_id = teams.id THEN
               games.team_two_timeouts
           ELSE
               games.team_one_timeouts END,
       (coalesce((SELECT SUM(event_type = 'Substitute') FROM gameEvents WHERE gameEvents.game_id = games.id AND gameEvents.team_id = teams.id), 0) = 0) AND teams.substitute_id is not null AND team_one_score + games.team_two_score <= 9
FROM games
         INNER JOIN tournaments on games.tournament_id = tournaments.id
         INNER JOIN teams on (games.team_two_id = teams.id or games.team_one_id = teams.id)
         INNER JOIN playerGameStats on playerGameStats.team_id = teams.id AND playerGameStats.game_id = games.id 
                    WHERE games.id = ?
                    GROUP BY teams.id
ORDER BY teams.id <> games.team_one_id""", (game_id,)).fetchall()
            players_query = c.execute("""
SELECT
            playerGameStats.team_id, people.name, people.searchable_name, playerGameStats.card_time_remaining <> 0,
            playerGameStats.points_scored,
            playerGameStats.aces_scored,
            playerGameStats.faults,      
            playerGameStats.double_faults,
            playerGameStats.rounds_on_court,
            playerGameStats.rounds_carded,
            playerGameStats.green_cards,
            playerGameStats.yellow_cards, 
            playerGameStats.red_cards
FROM games
         LEFT JOIN gameEvents on gameEvents.id = (SELECT Max(id) FROM gameEvents WHERE games.id = gameEvents.game_id)
         INNER JOIN playerGameStats on games.id = playerGameStats.game_id AND (gameEvents.event_type is null or (playerGameStats.player_id = gameEvents.team_one_left_id OR playerGameStats.player_id = gameEvents.team_one_right_id
            OR playerGameStats.player_id = gameEvents.team_two_left_id OR playerGameStats.player_id = gameEvents.team_two_right_id))
         INNER JOIN people on people.id = playerGameStats.player_id
         INNER JOIN teams on playerGameStats.team_id = teams.id
         WHERE games.id = ? 
         ORDER BY playerGameStats.team_id, teams.substitute_id = playerGameStats.player_id, (gameEvents.team_one_left_id = playerGameStats.player_id OR gameEvents.team_two_left_id = playerGameStats.player_id) DESC""",
                                      (game_id,)).fetchall()

            cards_query = c.execute("""SELECT people.name, playerGameStats.team_id, type, reason, hex 
            FROM punishments 
            INNER JOIN people on people.id = punishments.player_id
            INNER JOIN playerGameStats on playerGameStats.player_id = punishments.player_id and playerGameStats.team_id = punishments.team_id and playerGameStats.game_id = ?
         WHERE playerGameStats.tournament_id = punishments.tournament_id
         """, (game_id,)).fetchall()
            officials_query = c.execute("""SELECT searchable_name, name 
FROM officials INNER JOIN people on officials.person_id = people.id""").fetchall()

        @dataclass
        class Player:
            name: str
            searchable_name: str
            is_carded: bool
            stats: dict[str, object]

        @dataclass
        class Card:
            player: str
            team: int
            type: str
            reason: str
            hex: str

        @dataclass
        class Team:
            name: str
            searchable_name: str
            sort: int
            score: int
            image_url: str
            serving: bool
            card_time_remaining: int
            card_time: int
            green_carded: bool
            timeouts: int
            has_sub: bool
            players: list[Player]
            cards: list[Card]

        @dataclass
        class Game:
            id: int
            bye: bool
            official: str
            official_searchable_name: str
            scorer: str
            scorer_searchable_name: str
            started: bool
            someone_has_won: bool
            image: str
            faulted: bool
            server: str
            serve_side: str
            ended: bool
            has_scorer: bool
            round: int
            deletable: bool

        teams = {}
        cards = [Card(*i) for i in cards_query]
        game = Game(game_id, *game_query[2:], get_type_from_name(game_query[1], game_query[0]).manual_allowed()
                    )
        players = []
        player_headers = [
            "Points Scored",
            "Aces",
            "Faults",
            "Double Faults",
            "Rounds Played",
            "Rounds Benched",
            "Green Cards",
            "Yellow Cards",
            "Red Cards",
        ]
        for i in teams_query:
            teams[i[0]] = (Team(*i[1:], [], []))
            teams[i[0]].cards = [j for j in cards if j.team == i[0]]
        for i in players_query:
            player = Player(*i[1:4], {k: v for k, v in zip(player_headers, i[4:])})
            teams[i[0]].players.append(player)
            players.append(player)
        all_officials = officials_query
        # teams = sorted(list(teams.values()), key=lambda a: a.sort)
        teams = list(teams.values())
        if visual_swap:
            teams = list(reversed(teams))
        key = fetch_user()
        is_admin = key in [i.key for i in get_all_officials() if i.admin]
        team_one_players = sorted([((1 - i), v) for i, v in enumerate(teams[0].players[:2])], key=lambda a: a[1].searchable_name)
        team_two_players = sorted([((1 - i), v) for i, v in enumerate(teams[1].players[:2])], key=lambda a: a[1].searchable_name)

        # TODO: Write a permissions decorator for scorers and primary officials
        # if key not in [game.primary_official.key, game.scorer.key] and not is_admin:
        #     return _no_permissions()
        # el
        if visual_swap:
            team_one_players, team_two_players = team_two_players, team_one_players
        if game.bye:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This game is a bye!!",
                ),
                400,
            )
        elif not game.started:

            return (
                render_template(
                    "tournament_specific/game_editor/game_start.html",
                    players=[i.searchable_name for i in players],
                    teams=teams,
                    all_officials=all_officials,
                    teamOneNames=[f"{i.searchable_name}:{i.name}" for i in teams[0].players],
                    teamTwoNames=[f"{i.searchable_name}:{i.name}" for i in teams[1].players],
                    game=game,
                    swap=visual_str,
                    admin=True,  # key in [i.key for i in get_all_officials() if i.admin]
                ),
                200,
            )
        else:
            return (
                render_template(
                    f"tournament_specific/game_editor/edit_game.html",
                    players=[i.searchable_name for i in players],
                    teamOnePlayers=team_one_players,
                    teamTwoPlayers=team_two_players,
                    teamOneNames=[f"{i.searchable_name}:{i.name}" for i in teams[0].players],
                    teamTwoNames=[f"{i.searchable_name}:{i.name}" for i in teams[1].players],
                    swap=visual_str,
                    teams=teams,
                    enum_teams=enumerate(teams),
                    game=game,
                    timeout_time=manage_game.get_timeout_time(game_id) * 1000,
                    timeout_first=manage_game.get_timeout_caller(game_id),
                    match_points=0 if (max([i.score for i in teams]) < 10 or game.someone_has_won) else abs(
                        teams[0].score - teams[1].score),
                    VERBAL_WARNINGS=Config().use_warnings
                ),
                200,
            )

    @officials_only
    @app.get("/games/<game_id>/finalise")
    def finalise_game(game_id):
        visual_swap = request.args.get("swap", "false") == "true"
        visual_str = "true" if visual_swap else "false"

        with DatabaseManager() as c:
            game_query = c.execute("""
SELECT games.tournament_id,
       is_bye,
       po.name,
       po.searchable_name,
       ps.name,
       ps.searchable_name,
       tournaments.image_url,
       games.someone_has_won
FROM games
         INNER JOIN tournaments ON games.tournament_id = tournaments.id
         LEFT JOIN officials o ON games.official_id = o.id
         LEFT JOIN people po ON o.person_id = po.id
         LEFT JOIN officials s ON games.scorer_id = o.id
         LEFT JOIN people ps ON s.person_id = ps.id
         LEFT JOIN gameEvents ON games.id = gameEvents.game_id AND gameEvents.id =
                                                                  (SELECT MAX(id)
                                                                   FROM gameEvents
                                                                   WHERE games.id = gameEvents.game_id
                                                                     AND (gameEvents.event_type = 'Fault' or gameEvents.event_type = 'Score'))
         LEFT JOIN gameEvents lastGE ON games.id = lastGE.game_id AND lastGE.id =
                                                                     (SELECT MAX(id)
                                                                      FROM gameEvents
                                                                      WHERE games.id = gameEvents.game_id)
         LEFT JOIN people server on lastGE.player_to_serve_id = server.id
WHERE games.id = ?
            """, (game_id,)).fetchone()

            teams_query = c.execute("""SELECT teams.id, teams.name,
       teams.searchable_name,
       teams.id <> games.team_one_id,
       Case
           WHEN games.team_two_id = teams.id THEN
               games.team_two_score
           ELSE
               games.team_one_score END,
       case
           when teams.image_url is null
               then '/api/teams/image?name=blank'
           else
               teams.image_url
           end,
        teams.id = games.team_to_serve_id,
        IIF(sum(playerGameStats.red_cards) > 0, -1, max(playerGameStats.card_time_remaining)),
        max(IIF(playerGameStats.card_time is null, 0, playerGameStats.card_time)),
        max(playerGameStats.green_cards) > 0,
        Case
           WHEN games.team_two_id = teams.id THEN
               games.team_two_timeouts
           ELSE
               games.team_one_timeouts END
FROM games
         INNER JOIN tournaments on games.tournament_id = tournaments.id
         INNER JOIN teams on (games.team_two_id = teams.id or games.team_one_id = teams.id)
         INNER JOIN playerGameStats on playerGameStats.team_id = teams.id AND playerGameStats.game_id = games.id 
                    WHERE games.id = ?
                    GROUP BY teams.id
ORDER BY teams.id <> games.team_one_id
""", (game_id,)).fetchall()
            players_query = c.execute("""SELECT 
            playerGameStats.team_id, people.name, people.searchable_name,
            playerGameStats.points_scored,
            playerGameStats.aces_scored,
            playerGameStats.faults,      
            playerGameStats.double_faults,
            playerGameStats.rounds_on_court,
            playerGameStats.rounds_carded,
            playerGameStats.green_cards,
            playerGameStats.yellow_cards, 
            playerGameStats.red_cards
FROM games
         INNER JOIN playerGameStats on games.id = playerGameStats.game_id
         INNER JOIN people on people.id = playerGameStats.player_id
         WHERE game_id = ?
""", (game_id,)).fetchall()

        @dataclass
        class Player:
            name: str
            searchable_name: str
            stats: dict[str, object]

        @dataclass
        class Team:
            name: str
            searchable_name: str
            sort: int
            score: int
            image_url: str
            serving: bool
            card_time_remaining: int
            card_time: int
            green_carded: bool
            timeouts: int
            players: list[Player]

        @dataclass
        class Game:
            id: int
            bye: bool
            official: str
            official_searchable_name: str
            scorer: str
            scorer_searchable_name: str
            image: str
            someone_has_won: bool
            has_scorer: bool

        teams = {}
        game = Game(game_id, *game_query[1:], True)
        players = []
        player_headers = [
            "Points Scored",
            "Aces",
            "Faults",
            "Double Faults",
            "Rounds Played",
            "Rounds Benched",
            "Green Cards",
            "Yellow Cards",
            "Red Cards",
        ]
        for i in teams_query:
            teams[i[0]] = (Team(*i[1:], []))
        for i in players_query:
            player = Player(*i[1:3], {k: v for k, v in zip(player_headers, i[3:])})
            teams[i[0]].players.append(player)
            players.append(player)
        teams = list(teams.values())
        if visual_swap:
            teams = list(reversed(teams))
        key = fetch_user()
        is_admin = key in [i.key for i in get_all_officials() if i.admin]

        if game.someone_has_won or key in [
            i.key for i in get_all_officials() if i.admin
        ]:
            return (
                render_template(
                    "tournament_specific/game_editor/team_signatures.html",
                    swap=visual_str,
                    teams=teams,
                    game=game,
                    headers=player_headers
                ),
                200,
            )

    # TODO: UPDATE
    @app.get("/<tournament>/create")
    @officials_only
    def create_game(tournament):
        tournament_id = get_tournament_id(tournament)
        with DatabaseManager() as c:
            editable = c.execute(
                "SELECT fixtures_type from tournaments where id = ?",
                (tournament_id,),
            ).fetchone()
            teams = c.execute(
                """SELECT searchable_name, name FROM teams INNER JOIN tournamentTeams ON teams.id = tournamentTeams.team_id and tournamentTeams.tournament_id = ? order by searchable_name""",
                (tournament_id,)).fetchall()
            officials = c.execute(
                """SELECT searchable_name, name, password FROM officials INNER JOIN main.people on officials.person_id = people.id""").fetchall()
        if not get_type_from_name(editable[0], tournament_id).manual_allowed():
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This competition cannot be edited manually!",
                ),
                400,
            )
        key = fetch_user()
        # if key not in [i[2] for i in officials if i.admin]:
        #     officials = [i for i in officials if i.key == key]
        # else:
        official = [i for i in officials if i[2] == key]
        officials = official + [i for i in officials if i[2] != key]

        return (
            render_template(
                "tournament_specific/game_editor/create_game_teams.html",
                tournamentLink=link(tournament),
                officials=officials,
                teams=teams,
            ),
            200,
        )

    # TODO: UPDATE
    @app.get("/<tournament>/create_players")
    def create_game_players(tournament):
        tournament_id = get_tournament_id(tournament)
        with DatabaseManager() as c:
            editable = c.execute(
                "SELECT fixtures_type from tournaments where id = ?",
                (tournament_id,),
            ).fetchone()
            players = c.execute(
                """SELECT searchable_name, name FROM people order by searchable_name""").fetchall()
            officials = c.execute(
                """SELECT searchable_name, name, password FROM officials INNER JOIN main.people on officials.person_id = people.id""").fetchall()
        if not get_type_from_name(editable[0], tournament_id).manual_allowed():
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This competition cannot be edited manually!",
                ),
                400,
            )

        key = fetch_user()
        # if key not in [i.key for i in get_all_officials() if i.admin]:
        #     officials = [i for i in officials if i.key == key]
        official = [i for i in officials if i[2] == key]
        officials = official + [i for i in officials if i[2] != key]
        return (
            render_template(
                "tournament_specific/game_editor/create_game_players.html",
                tournamentLink=link(tournament),
                officials=officials,
                players=players,
            ),
            200,
        )

    @app.get("/teams/")
    def universal_stats_directory_site():
        return team_directory_site(None)

    @app.get("/teams/<team_name>/")
    def universal_stats_site(team_name):
        return team_site(None, team_name)

    @app.get("/ladder/")
    def universal_ladder_site():
        return ladder_site(None)

    @app.get("/players/")
    def universal_players_site():
        return players_site(None)

    @app.get("/players/detailed/")
    def universal_detailed_players_site():
        return detailed_players_site(None)

    @app.get("/players/<player_name>/")
    def universal_player_stats(player_name):
        return player_stats(None, player_name)

    @app.get("/officials/<nice_name>/")
    def universal_official_site(nice_name):
        return official_site(None, nice_name)

    @app.get("/officials/")
    def universal_official_directory_site():
        return official_directory_site(None)
