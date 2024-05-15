import time
from collections import defaultdict
from dataclasses import dataclass
from flask import render_template, request, redirect, Response

from FixtureMakers.FixtureMaker import get_type_from_name
from structure.AllTournament import (
    get_all_games,
    get_all_officials,
)
from structure.GameUtils import game_string_to_commentary
from structure.Tournament import Tournament
from structure.UniversalTournament import UniversalTournament
from utils.sidebar_wrapper import render_template_sidebar
from utils.statistics import get_player_stats, get_player_stats_categories
from utils.permissions import (
    admin_only,
    fetch_user,
    officials_only,
    _no_permissions,
    user_on_mobile,
)  # Temporary till i make a function that can handle dynamic/game permissions

from utils.databaseManager import DatabaseManager, get_tournament_id
from utils.util import fixture_sorter
from website.website import numbers, sign


def priority_to_classname(p):
    if p == 1:
        return ""
    sizes = ["sm", "md", "lg", "xl"]
    return f"d-none d-{sizes[p-2]}-table-cell"


def link(tournament):
    return f"{tournament}/" if tournament else ""


def add_tournament_specific(app, comps_in: dict[str, Tournament]):
    comps = comps_in.copy()
    comps[None] = UniversalTournament()

    @app.get("/<tournament>/")  # TODO: Implement pooled
    def home_page(tournament: str):
        tournamentId: int = get_tournament_id(tournament)
        if tournamentId is None:
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
                                name, teams.searchableName, gamesWon, gamesPlayed 
                                FROM tournamentTeams 
                                INNER JOIN teams ON tournamentTeams.teamId = teams.id 
                                WHERE tournamentId = ? 
                                ORDER BY 
                                    gamesWon DESC, 
                                    gamesPlayed ASC 
                                LIMIT 10;""",
                (tournamentId,),
            ).fetchall()
            ladder = [
                [
                    None,
                    [(n, LadderTeam(*team)) for n, team in enumerate(teams, start=1)],
                ]
            ]  # there has to be a reason this is the required syntax but i can't work it out

            games = c.execute(
                """
                            SELECT 
                                serving.name, receiving.name, servingScore, receivingScore, games.id 
                                FROM games 
                                INNER JOIN teams AS serving ON games.servingTeam = serving.id 
                                INNER JOIN teams as receiving ON games.receivingTeam = receiving.id 
                                WHERE 
                                    tournamentId = ? AND 
                                    games.bestPlayer = NULL;
                            """,
                (tournamentId,),
            ).fetchall()
            ongoing_games = [
                Game(game[:2], f"{game[2]} - {game[3]}", game[4]) for game in games
            ]

            games = c.execute(
                """
                            SELECT 
                                serving.name, receiving.name, servingScore, receivingScore, games.id
                                FROM games 
                                INNER JOIN teams AS serving ON games.servingTeam = serving.id 
                                INNER JOIN teams as receiving ON games.receivingTeam = receiving.id 
                                WHERE tournamentId = ? AND
                                CASE -- if there is finals, return the finals, else return the last round
                                    WHEN (SELECT count(*) FROM games WHERE tournamentId = ? AND isFinal = 1) > 0 THEN
                                        isFinal = 1
                                    ELSE 
                                        round = (SELECT max(round) FROM games WHERE tournamentId = ?) 
                                END;""",
                (tournamentId,) * 3,
            ).fetchall()
            current_round = [
                Game(game[:2], f"{game[2]} - {game[3]}", game[4]) for game in games
            ]

            playerList = c.execute(
                """
                                SELECT 
                                    people.name, searchableName, sum(isBestPlayer), sum(points), sum(aces), sum(redCards+yellowCards) 
                                    FROM playerGameStats 
                                    INNER JOIN people ON playerId = people.id 
                                    WHERE 
                                        tournamentId = ? AND
                                        isFinal = 0
                                    GROUP BY playerId 
                                    ORDER BY 
                                        sum(isBestPlayer) DESC, 
                                        sum(points) DESC, 
                                        sum(aces) DESC, 
                                        sum(redCards+yellowCards+greenCards) ASC  
                                    LIMIT 10;""",
                (tournamentId,),
            ).fetchall()
            players = [Player(*player) for player in playerList]

            notes = (
                c.execute(
                    "SELECT notes FROM tournaments WHERE id = ?", (tournamentId,)
                ).fetchone()[0]
                or "Notices will appear here when posted"
            )
            tourney = c.execute(
                "SELECT name, searchableName, fixturesGenerator from tournaments where id = ?",
                (tournamentId,),
            ).fetchone()
            in_progress = c.execute(
                "SELECT not(isFinished) FROM tournaments WHERE id=?", (tournamentId,)
            ).fetchone()[0]
            iseditable = get_type_from_name(tourney[2]).manual_allowed()
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
                    tournament=link(tournament),
                    ladder=ladder,
                ),
                200,
            )

    @app.get("/<tournament>/fixtures/")
    def fixtures(tournament):
        @dataclass
        class Game:
            teams: list[str]
            score_string: str
            id: int

        with DatabaseManager() as c:
            tournamentId = get_tournament_id(tournament)
            games = c.execute(
                """
                            SELECT 
                                serving.name, receiving.name, servingScore, receivingScore, games.id, round
                                FROM games 
                                INNER JOIN teams AS serving ON games.servingTeam = serving.id 
                                INNER JOIN teams AS receiving ON games.receivingTeam = receiving.id
                                -- INNER JOIN people ON games.bestPlayer = people.id 
                                WHERE 
                                    tournamentId = ? AND
                                    isFinal = 0;""",
                (tournamentId,),
            ).fetchall()
            # me when i criticize Jareds code then write this abomination
            fixtures = defaultdict(list)
            for game in games:
                fixtures[game[5]].append(
                    Game(game[:2], f"{game[2]} - {game[3]}", game[4])
                )

            games = c.execute(
                """
                            SELECT 
                                serving.name, receiving.name, servingScore, receivingScore, games.id, round
                                FROM games 
                                INNER JOIN teams AS serving ON games.servingTeam = serving.id 
                                INNER JOIN teams AS receiving ON games.receivingTeam = receiving.id
                                -- INNER JOIN people ON games.bestPlayer = people.id 
                                WHERE 
                                    tournamentId = ? AND
                                    isFinal = 1;""",
                (tournamentId,),
            ).fetchall()
            # idk something about glass houses?
            finals = defaultdict(list)
            for game in games:
                finals[game[5]].append(
                    Game(game[:2], f"{game[2]} - {game[3]}", game[4])
                )
        return (
            render_template_sidebar(
                "tournament_specific/site.html",
                fixtures=fixtures.items(),
                finals=finals.items(),
                tournament=link(tournament),
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
            umpire: str
            umpireSearchableName: str
            scorer: str
            scorerSearchableName: str
            court: int
            court_name: str

        @dataclass
        class Tourney:
            twoCourts: bool
            scorer: bool

        with DatabaseManager() as c:
            tournamentId = get_tournament_id(tournament)

            games = c.execute(
                """SELECT 
                        serving.name, receiving.name, servingScore, receivingScore, games.id, 
                        umpire.name, umpire.searchableName, scorer.name, scorer.searchableName, 
                        court, round
                        FROM games 
                        INNER JOIN teams AS serving ON games.servingTeam = serving.id 
                        INNER JOIN teams AS receiving ON games.receivingTeam = receiving.id
                        LEFT JOIN officials AS u ON games.official = u.id
                            LEFT JOIN people AS umpire ON u.personId = umpire.id
                        LEFT JOIN officials AS s ON games.scorer = s.id
                            LEFT JOIN people AS scorer ON s.personId = scorer.id
                        WHERE
                            tournamentId = ? AND
                            isFinal = 0;
                            """,
                (tournamentId,),
            )
            fixtures = defaultdict(list)
            for game in games:
                fixtures[game[-1]].append(
                    GameDetailed(
                        game[:2],
                        f"{game[2]} - {game[3]}",
                        game[4],
                        game[5],
                        game[6],
                        game[7],
                        game[8],
                        game[9],
                        {-1: "-", 0: "Court 1", 1: "Court 2"}.get(game[9]),
                    )
                )

            games = c.execute(
                """SELECT 
                        serving.name, receiving.name, servingScore, receivingScore, games.id, 
                        umpire.name, umpire.searchableName, scorer.name, scorer.searchableName, 
                        court, round
                        FROM games 
                        INNER JOIN teams AS serving ON games.servingTeam = serving.id 
                        INNER JOIN teams AS receiving ON games.receivingTeam = receiving.id
                        LEFT JOIN officials AS u ON games.official = u.id
                            LEFT JOIN people AS umpire ON u.personId = umpire.id
                        LEFT JOIN officials AS s ON games.scorer = s.id
                            LEFT JOIN people AS scorer ON s.personId = scorer.id
                        WHERE
                            tournamentId = ? AND
                            isFinal = 1;
                            """,
                (tournamentId,),
            )
            finals = defaultdict(list)
            for game in games:
                finals[game[-1]].append(
                    GameDetailed(
                        game[:2],
                        f"{game[2]} - {game[3]}",
                        game[4],
                        game[5],
                        game[6],
                        game[7],
                        game[8],
                        game[9],
                        {-1: "-", 0: "Court 1", 1: "Court 2"}.get(game[9]),
                    )
                )

            t = Tourney(
                *c.execute(
                    """SELECT
                                twoCourts, count(scorer)>0
                                FROM tournaments
                                INNER JOIN games ON games.tournamentId = tournaments.id
                                WHERE tournaments.id = ?;""",
                    (tournamentId,),
                ).fetchone()
            )

        return (
            render_template_sidebar(
                "tournament_specific/site_detailed.html",
                fixtures=fixtures.items(),
                finals=finals.items(),
                tournament=link(tournament),
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
            tournamentId = get_tournament_id(tournament)
            teams = c.execute(
                """
                            SELECT 
                                name, searchableName, 
                                    case 
                                        when imageURL is null 
                                            then "/api/teams/image?name=blank" 
                                        else 
                                            imageURL
                                    end  
                                FROM teams 
                                INNER JOIN tournamentTeams ON teams.id = tournamentTeams.teamId 
                                WHERE tournamentId = ? AND
                                tournamentTeams.gamesPlayed > 0;""",
                (tournamentId,),
            ).fetchall()
            teams = [Team(*team) for team in teams]

        return (
            render_template_sidebar(
                "tournament_specific/stats.html",
                teams=teams,
                tournament=link(tournament),
            ),
            200,
        )

    @app.get("/<tournament>/teams/<team_name>/")
    def team_site(tournament, team_name):
        @dataclass
        class TeamStats:
            name: str
            searchableName: str
            image: str
            elo: float
            gamesPlayed: int
            gamesWon: int
            gamesLost: int
            winPercentage: str
            greenCards: int
            yellowCards: int
            redCards: int
            faults: int
            timeoutsCalled: int
            pointsFor: int
            pointsAgainst: int
            pointDifference: int

        @dataclass
        class PlayerStats:
            name: str
            searchableName: str
            bestPlayer: int
            elo: float
            points: int
            aces: int
            faults: int
            doubleFaults: int
            greenCards: int
            yellowCards: int
            redCards: int
            roundsOnCourt: int
            roundsCarded: int

        with DatabaseManager() as c:
            tournamentId = get_tournament_id(tournament)
            team = c.execute(
                """
                        SELECT 
                            name, searchableName, 
                                case 
                                    when imageURL is null 
                                        then "/api/teams/image?name=blank" 
                                    else 
                                        imageURL
                                end  
                            FROM teams 
                            WHERE searchableName = ?;""",
                (team_name,),
            ).fetchone()

            if not team:
                return (
                    render_template(
                        "tournament_specific/game_editor/game_done.html",
                        error="This is not a real team",
                    ),
                    400,
                )
            team = TeamStats(*team)
            players = c.execute(
                """
                        SELECT 
                            name, searchableName, sum(isBestPlayer), sum(points), sum(aces), sum(redCards+yellowCards) 
                            FROM playerGameStats 
                            INNER JOIN people ON playerId = people.id 
                            WHERE 
                                tournamentId = ? AND
                                teamId = (SELECT id FROM teams WHERE searchableName = ?)
                            GROUP BY playerId 
                            ORDER BY 
                                sum(isBestPlayer) DESC, 
                                sum(points) DESC, 
                                sum(aces) DESC, 
                                sum(redCards+yellowCards+greenCards);""",
                (tournamentId, team_name),
            ).fetchall()
        if team_name not in [i.nice_name() for i in comps[tournament].teams]:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This is not a real team",
                ),
                400,
            )
        team = [i for i in comps[tournament].teams if team_name == i.nice_name()][0]
        recent_games = []
        upcoming_games = []
        for i in comps[tournament].games_to_list():
            if team.nice_name() not in [j.nice_name() for j in i.teams] or i.bye:
                continue
            if i.started:
                gt = next(j for j in i.teams if j.nice_name() == team_name)
                s = " <+0>"
                if gt.elo_delta:
                    s = f" <{sign(gt.elo_delta)}{round(abs(gt.elo_delta), 2)}>"
                recent_games.append(
                    (
                        repr(i) + f" ({i.score_string}){s}",
                        i.id,
                        i.tournament.nice_name(),
                    )
                )
            else:
                upcoming_games.append((repr(i), i.id, i.tournament.nice_name()))
        while len(recent_games) + len(upcoming_games) > 20:
            if len(recent_games) > 10:
                recent_games.pop(0)
            else:
                upcoming_games.pop(0)
        players = [
            (
                i.name,
                i.nice_name(),
                [
                    (k, v)
                    for k, v in get_player_stats(
                        i.tournament, i, detail=1, team=team
                    ).items()
                ],
            )
            for i in team.players
        ]
        return (
            render_template_sidebar(
                "tournament_specific/each_team_stats.html",
                stats=[(k, v) for k, v in team.get_stats().items()],
                team=team,
                recent_games=recent_games,
                upcoming_games=upcoming_games,
                tournament=link(tournament),
                players=players,
            ),
            200,
        )

    @app.get("/<tournament>/games/<game_id>/display")
    def scoreboard(tournament, game_id):
        if int(game_id) >= len(comps[tournament].games_to_list()):
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="Game Does not exist",
                ),
                400,
            )

        game = comps[tournament].get_game(int(game_id))
        visual_swap = request.args.get("swap", "false") == "true"
        teams = game.teams
        if visual_swap:
            teams = list(reversed(teams))
        players = game.current_players
        round_number = game.round_number + 1
        if not game.started:
            status = "Waiting for toss"
        elif game.in_timeout:
            status = "In Timeout"
        elif not game.game_ended:
            status = "Game in Progress"
        elif not game.best_player:
            status = "Finished"
        else:
            status = "Official"
        return (
            render_template_sidebar(
                "tournament_specific/scoreboard.html",
                game=game,
                status=status,
                players=players,
                teams=teams,
                official=game.primary_official,
                roundNumber=round_number,
                update_count=game.update_count,
                tournament=link(tournament),
                timeout_time=max([i.time_out_time + 30 for i in game.teams]) * 1000,
                serve_time=(game.serve_clock + 8) * 1000,
            ),
            200,
        )

    @app.get("/<tournament>/games/<game_id>/")
    def game_site(tournament, game_id):
        with DatabaseManager() as c:
            players = c.execute(
                """SELECT people.name,
                                       SUM(eloChange.eloChange) + 1500     as elo,
                                       (SELECT eloChange
                                        from eloChange
                                        where eloChange.playerId = playerGameStats.playerId
                                          and eloChange.gameId = games.id) as eloDelta,
                                       playerGameStats.points,
                                       playerGameStats.aces,
                                       playerGameStats.faults, --5
                                       playerGameStats.doubleFaults,
                                       playerGameStats.roundsPlayed,
                                       playerGameStats.roundsBenched,
                                       playerGameStats.greenCards,
                                       playerGameStats.yellowCards, --10
                                       playerGameStats.redCards,
                                       games.isBye,   --i[12]
                                       tournaments.name,
                                       tournaments.searchableName,
                                       teams.name, --15
                                       teams.searchableName,
                                       games.servingTeam = teams.id,
                                       games.servingScore,
                                       games.receivingScore,
                                       po.name, --20
                                       po.searchableName,
                                       ps.name,
                                       ps.searchableName,
                                       games.court,
                                       games.round,--25
                                       best.name,
                                       best.searchableName,
                                       games.startTime,
                                       tournaments.searchableName,
                                       teams.name, --30
                                       teams.searchableName,
                                       teams.imageURL
                                FROM games
                                         INNER JOIN playerGameStats on playerGameStats.gameId = games.id
                                         INNER JOIN tournaments on tournaments.id = games.tournamentId
                                         INNER JOIN officials o on o.id = games.official
                                         INNER JOIN people po on po.id = o.id
                                         INNER JOIN officials s on s.id = games.official
                                         INNER JOIN people ps on o.id = s.id
                                         INNER JOIN people on people.id = playerGameStats.playerId
                                         INNER JOIN people best on best.id = games.bestPlayer
                                         INNER JOIN teams on teams.id = playerGameStats.teamId
                                         INNER JOIN eloChange on games.id >= eloChange.gameId and eloChange.playerId = playerGameStats.playerId
                                WHERE games.id = ?
                                GROUP BY people.name
                                order by teams.id = games.servingTeam, playerGameStats.sideOfCourt;""",
                (game_id,),
            ).fetchall()
        if not players:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="Game Does not exist",
                ),
                400,
            )

        @dataclass
        class Player:
            name: str
            stats: dict[str, any]

        headers = [
            "ELO",
            "ELO Delta",
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

        def make_player(row):
            name = row[0]
            stats = row[1:11]

            return Player(name, {k: v for k, v in zip(headers, stats)})

        @dataclass
        class Team:
            players: list[Player]
            image: str
            name: str
            searchableName: str

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

        playerStats = []
        teams = {}
        for i in players:
            pl = make_player(i)
            playerStats.append(pl)
            if i[3] not in teams:
                teams[i[3]] = Team([], i[32] if i[32] else "", i[30], i[31])
            teams[i[3]].players.append(pl)
        teams = list(teams.values())
        time_float = float(players[0][28])

        game = Game(
            playerStats,
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
        )

        best = game.bestSearchableName if game.bestSearchableName else "TBD"

        round_number = game.round
        prev_matches = []
        prev_matches = prev_matches or [("No other matches", -1, players[0][29])]
        status = "Fix me"
        return (
            render_template_sidebar(
                "tournament_specific/game_page.html",
                game=game,
                status=status,
                teams=teams,
                best=best,
                team_headings=teams_headings,
                player_headings=headers,
                roundNumber=round_number,
                prev_matches=prev_matches,
                tournament=link(tournament),
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
        with DatabaseManager() as c:
            c.execute("SELECT ")
        ladder = comps[tournament].ladder()
        if isinstance(ladder[0], list):
            ladder = [
                (f"Pool {numbers[i]}", list(enumerate(l, start=1)))
                for i, l in enumerate(ladder)
            ]
        else:
            ladder = [("", list(enumerate(ladder, start=1)))]
        ladder = [(i if len(i) <= 10 else i[:10]) for i in ladder]
        teams = [
            (
                [
                    (
                        j.short_name,
                        j.nice_name(),
                        j.image(),
                        [
                            (v, priority_to_classname(priority[k]))
                            for k, v in j.get_stats().items()
                        ],
                    )
                    for _, j in l[1]
                    if j.games_played > 0
                    or len(comps[tournament].teams) < 15
                    or not any(
                        not i.super_bye for i in comps[tournament].games_to_list()
                    )
                ],
                l[0],
                k,
            )
            for k, l in enumerate(ladder)
        ]
        headers = [
            (i, priority_to_classname(priority[i]))
            for i in (
                ["Team Names"] + [i for i in comps[tournament].teams[0].get_stats()]
            )
        ]
        return (
            render_template_sidebar(
                "tournament_specific/ladder.html",
                headers=[(i - 1, k, v) for i, (k, v) in enumerate(headers)],
                teams=teams,
                tournament=link(tournament),
            ),
            200,
        )

    @app.get("/<tournament>/players/")
    def players_site(tournament):
        priority = {
            "Name": 1,
            "B&F Votes": 1,
            "Elo": 2,
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
        players = [
            (
                i.name,
                i.team.nice_name(),
                i.nice_name(),
                [
                    (v, priority_to_classname(priority[k]))
                    for k, v in i.get_stats().items()
                ],
            )
            for i in comps[tournament].players
            if (i.get_stats()["Games Played"] or len(comps[tournament].fixtures) < 2)
            and not i.nice_name().startswith("null")
        ]
        headers = ["Name"] + [
            i for i in comps[tournament].teams[0].players[0].get_stats()
        ]
        return (
            render_template_sidebar(
                "tournament_specific/players.html",
                headers=[
                    (i - 1, k, priority_to_classname(priority[k]))
                    for i, k in enumerate(headers)
                ],
                players=sorted(players),
                tournament=link(tournament),
            ),
            200,
        )

    @app.get("/<tournament>/players/detailed")
    def detailed_players_site(tournament):
        players = [
            (
                i.name,
                i.team.nice_name(),
                i.nice_name(),
                i.get_stats_detailed().values(),
            )
            for i in comps[tournament].players
            if (i.get_stats()["Games Played"] or len(comps[tournament].fixtures) < 2)
            and not i.nice_name().startswith("null")
        ]
        headers = ["Name"] + [
            i for i in comps[tournament].teams[0].players[0].get_stats_detailed()
        ]
        return (
            render_template_sidebar(
                "tournament_specific/players_detailed.html",
                headers=[(i - 1, k) for i, k in enumerate(headers)],
                players=sorted(players),
                total=get_player_stats(comps[tournament], None, detail=2),
                tournament=link(tournament),
            ),
            200,
        )

    @app.get("/<tournament>/players/<player_name>/")
    def player_stats(tournament, player_name):
        if player_name not in [i.nice_name() for i in comps[tournament].players]:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This is not a real player",
                ),
                400,
            )
        player = [i for i in comps[tournament].players if player_name == i.nice_name()][
            0
        ]
        recent_games = []
        upcoming_games = []
        for i in comps[tournament].games_to_list():
            if player_name not in [j.nice_name() for j in i.current_players] or i.bye:
                continue
            gt = next(
                t for t in i.teams if player_name in [j.nice_name() for j in t.players]
            )
            gp = next(p for p in gt.players if player_name == p.nice_name())
            s = " <+0>"
            if gt.elo_delta:
                s = f" <{sign(gp.elo_delta)}{round(abs(gp.elo_delta), 2)}>"
            if i.started:
                recent_games.append(
                    (
                        i.full_name + s,
                        i.id,
                        i.tournament.nice_name(),
                    )
                )
            else:
                upcoming_games.append((repr(i), i.id, i.tournament.nice_name()))
        while len(recent_games) + len(upcoming_games) > 20:
            if len(recent_games) > 10:
                recent_games.pop(0)
            else:
                upcoming_games.pop(0)
        if user_on_mobile():
            return (
                render_template_sidebar(
                    "tournament_specific/player_stats.html",
                    stats=[
                        (k, v)
                        for k, v in get_player_stats(
                            player.tournament, player, detail=2
                        ).items()
                    ],
                    name=player.name,
                    player=player,
                    recent_games=recent_games,
                    upcoming_games=upcoming_games,
                    tournament=link(tournament),
                ),
                200,
            )
        else:
            return (
                render_template_sidebar(
                    "tournament_specific/new_player_stats.html",
                    stats=[
                        (k, v)
                        for k, v in get_player_stats(
                            player.tournament, player, detail=2
                        ).items()
                    ],
                    name=player.name,
                    player=player,
                    recent_games=recent_games,
                    upcoming_games=upcoming_games,
                    insights=comps[tournament]
                    .games_to_list()[0]
                    .current_players[0]
                    .get_stats_detailed()
                    .keys(),
                    tournament=link(tournament),
                ),
                200,
            )

    @app.get("/<tournament>/officials/<nice_name>/")
    def official_site(tournament, nice_name):
        if nice_name not in [i.nice_name() for i in comps[tournament].officials]:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="Official Does not exist",
                ),
                400,
            )
        official = [
            i for i in comps[tournament].officials if i.nice_name() == nice_name
        ][0]
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
        with DatabaseManager() as c:
            values = c.execute(
                """SELECT
                                   SUM(punishments.color = "Green"),
                                   SUM(punishments.color = "Yellow"),
                                   SUM(punishments.color = "Red"),
                                   COUNT(punishments.id),
                                   ROUND(CAST(COUNT(punishments.id) AS REAL) / COUNT(DISTINCT games.id), 2),
                                   (SELECT SUM(faults)
                                    FROM games
                                             INNER JOIN playerGameStats on games.id = playerGameStats.gameId
                                    WHERE games.official = officials.id),
                                   ROUND(CAST((SELECT SUM(faults)
                                         FROM games
                                                  INNER JOIN playerGameStats on games.id = playerGameStats.gameId
                                         WHERE games.official = officials.id) AS REAL) / COUNT(DISTINCT games.id), 2),
                                   COUNT(DISTINCT games.id),
                                   COUNT((SELECT games.id FROM games WHERE games.scorer = officials.id)),
                                   SUM((SELECT servingScore + receivingScore FROM games WHERE games.official = officials.id))
                            
                                    FROM officials
                                             INNER JOIN people on people.id = officials.personId
                                             INNER JOIN games on games.official = officials.id
                                             LEFT JOIN punishments on games.id = punishments.gameId
                                    WHERE people.searchableName = ?
            """,
                (nice_name,),
            ).fetchall()
            games = c.execute(
                """SELECT DISTINCT games.id,
                tournaments.searchableName,
                po.searchableName = ?,
                round,
                st.name,
                rt.name,
                servingScore,
                receivingScore
            FROM games
                     INNER JOIN officials o on games.official = o.id
                     INNER JOIN tournaments on games.tournamentId = tournaments.id
                     LEFT JOIN teams st on st.id = games.servingTeam
                     LEFT JOIN teams rt on rt.id = games.receivingTeam
                     LEFT JOIN officials s on games.scorer = s.id
                     LEFT JOIN main.people po on po.id = o.personId
                     LEFT JOIN main.people ps on ps.id = s.personId
            WHERE po.searchableName = ?
               or ps.searchableName = ?
            ORDER BY games.id;
            """,
                (nice_name, nice_name, nice_name),
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
                name=official.name,
                link=official.nice_name(),
                stats=zip(titles, values[0]),
                games=recent_games,
                tournament=link(tournament),
            ),
            200,
        )

    @app.get("/<tournament>/officials/")
    def official_directory_site(tournament):
        with DatabaseManager() as c:
            official = c.execute(
                """
            SELECT name, searchableName from officials INNER JOIN people on people.id = officials.personId
            """
            ).fetchall()
        return (
            render_template_sidebar(
                "tournament_specific/all_officials.html",
                officials=official,
                tournament=link(tournament),
            ),
            200,
        )

    @app.get("/<tournament>/games/<game_id>/edit/")
    @officials_only
    def game_editor(tournament, game_id):
        if int(game_id) >= len(comps[tournament].games_to_list()):
            raise Exception("Game Does not exist!!")
        visual_swap = request.args.get("swap", "false") == "true"
        visual_str = "true" if visual_swap else "false"
        game = comps[tournament].get_game(int(game_id))
        teams = game.teams
        if visual_swap:
            teams = list(reversed(teams))
        key = fetch_user()
        is_admin = key in [i.key for i in get_all_officials() if i.admin]
        players = [i for i in game.current_players]
        team_one_players = [((1 - i), v) for i, v in enumerate(teams[0].players[:2])]
        team_two_players = [((1 - i), v) for i, v in enumerate(teams[1].players[:2])]

        # TODO: Write a permissions decorator for scorers and primary officials
        if key not in [game.primary_official.key, game.scorer.key] and not is_admin:
            return _no_permissions()
        elif game.bye:
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
                    players=[i.tidy_name() for i in players],
                    teams=teams,
                    game=game,
                    tournament=link(tournament),
                    swap=visual_str,
                    admin=key in [i.key for i in get_all_officials() if i.admin],
                ),
                200,
            )
        elif not game.game_ended:
            # for i in teams:
            #     i.end_timeout()
            timeout_team = max(game.teams, key=lambda a: a.time_out_time)
            return (
                render_template(
                    f"tournament_specific/{'' if not is_admin else 'admin/'}game_editor/edit_game.html",
                    players=[i.tidy_name() for i in players],
                    teamOnePlayers=team_one_players,
                    teamTwoPlayers=team_two_players,
                    swap=visual_str,
                    teams=teams,
                    enum_teams=enumerate(teams),
                    game=game,
                    timeout_time=30000
                    + max(i.time_out_time for i in game.teams) * 1000,
                    timeout_first=1 - game.teams.index(timeout_team),
                    tournament=link(tournament),
                ),
                200,
            )
        elif game.protested is None:
            team_dicts = [i.get_stats() for i in teams]
            return (
                render_template(
                    "tournament_specific/game_editor/team_signatures.html",
                    players=[i.tidy_name() for i in players],
                    swap=visual_str,
                    teams=teams,
                    game=game,
                    headers=[i for i in players[0].get_stats().keys()],
                    stats=[(i, *[j[i] for j in team_dicts]) for i in team_dicts[0]],
                    tournament=link(tournament),
                ),
                200,
            )
        elif not game.best_player or key in [
            i.key for i in get_all_officials() if i.admin
        ]:
            return (
                render_template(
                    "tournament_specific/game_editor/finalise.html",
                    players=[i.tidy_name() for i in players],
                    swap=visual_str,
                    teams=teams,
                    game=game,
                    cards=enumerate(game.cards, start=1),
                    tournament=link(tournament),
                ),
                200,
            )
        else:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This game has already been completed!",
                ),
                400,
            )

    @app.get("/<tournament>/create")
    @officials_only
    def create_game(tournament):
        if not comps[tournament].fixtures_class.manual_allowed():
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This competition cannot be edited manually!",
                ),
                400,
            )
        elif any(
            [not (i.best_player or i.bye) for i in comps[tournament].games_to_list()]
        ):
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="There is already a game in progress!",
                ),
                400,
            )
        teams = comps[tournament].teams
        next_id = (
            comps[tournament].fixtures[-1][-1].id if comps[tournament].fixtures else 0
        )
        officials = comps[tournament].officials.copy()
        key = fetch_user()

        if key not in [i.key for i in get_all_officials() if i.admin]:
            officials = [i for i in officials if i.key == key]
        else:
            official = [i for i in officials if i.key == key]
            officials = official + [i for i in officials if i.key != key]

        return (
            render_template(
                "tournament_specific/game_editor/create_game_teams.html",
                tournament=link(tournament),
                officials=officials,
                teams=teams,
                id=next_id,
            ),
            200,
        )

    @app.get("/<tournament>/round")
    @admin_only
    def new_round_site(tournament):
        if not comps[tournament].fixtures_class.manual_allowed():
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This competition cannot be edited manually!",
                ),
                400,
            )
        elif any(
            [not (i.best_player or i.bye) for i in comps[tournament].games_to_list()]
        ):
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="There is already a game in progress!",
                ),
                400,
            )

        comps[tournament].update_games(True)
        comps[tournament].update_games()
        comps[tournament].save()
        return redirect(f"/{comps[tournament].nice_name()}/", code=302)

    @app.get("/<tournament>/createPlayers")
    def create_game_players(tournament):
        if not comps[tournament].fixtures_class.manual_allowed():
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This competition cannot be edited manually!",
                ),
                400,
            )
        elif any(
            [not (i.best_player or i.bye) for i in comps[tournament].games_to_list()]
        ):
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="There is already a game in progress!",
                ),
                400,
            )
        players = sorted(comps[tournament].players, key=lambda a: a.nice_name())
        next_id = (
            comps[tournament].fixtures[-1][-1].id if comps[tournament].fixtures else 0
        )
        officials = comps[tournament].officials

        key = fetch_user()
        if key not in [i.key for i in get_all_officials() if i.admin]:
            officials = [i for i in officials if i.key == key]
        else:
            official = [i for i in officials if i.key == key]
            officials = official + [i for i in officials if i.key != key]
        return (
            render_template(
                "tournament_specific/game_editor/create_game_players.html",
                tournament=link(tournament),
                officials=officials,
                players=players,
            ),
            200,
        )

    @app.get("/<tournament>/raw/")
    def raw_tournament(tournament):
        players = comps[tournament].players
        headers = []
        for k, v in get_player_stats(
            players[0].tournament, players[0], detail=3
        ).items():
            if isinstance(v, dict):
                headers += [f"{k} {i}" for i in v]
            else:
                headers.append(k)
        string = "Name," + ",".join(headers)
        for i in players:
            to_add = []
            for j in get_player_stats(i.tournament, i, detail=3).values():
                if isinstance(j, dict):
                    to_add += j.values()
                else:
                    to_add.append(j)
            string += "\n"
            string += ",".join([i.name] + [str(j) for j in to_add])
        response = Response(string, content_type="text/csv")
        response.headers[
            "Content-Disposition"
        ] = f"attachment; filename={comps[tournament].nice_name()}.csv"
        return response

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

    @app.get("/players/detailed")
    def unviersal_detailed_players_site():
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

    @app.get("/raw/")
    def raw():
        return raw_tournament(None)
