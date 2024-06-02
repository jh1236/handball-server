import time
from collections import defaultdict
from dataclasses import dataclass

from flask import render_template, request, redirect, Response

from FixtureMakers.FixtureMaker import get_type_from_name
from structure.AllTournament import (
    get_all_officials,
)
from structure.Tournament import Tournament
from structure.UniversalTournament import UniversalTournament
from utils.databaseManager import DatabaseManager, get_tournament_id
from utils.permissions import (
    admin_only,
    fetch_user,
    officials_only,
    user_on_mobile,
)  # Temporary till i make a function that can handle dynamic/game permissions
from utils.sidebar_wrapper import render_template_sidebar
from utils.statistics import get_player_stats
from website.website import numbers

VERBAL_WARNINGS = True


def priority_to_classname(p):
    if p == 1:
        return ""
    sizes = ["sm", "md", "lg", "xl"]
    return f"d-none d-{sizes[p - 2]}-table-cell"


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
                                serving.name, receiving.name, teamOneScore, teamTwoScore, games.id 
                                FROM games 
                                INNER JOIN teams AS serving ON games.teamOne = serving.id 
                                INNER JOIN teams as receiving ON games.teamTwo = receiving.id 
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
                                serving.name, receiving.name, teamOneScore, teamTwoScore, games.id
                                FROM games 
                                INNER JOIN teams AS serving ON games.teamOne = serving.id 
                                INNER JOIN teams as receiving ON games.teamTwo = receiving.id 
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
                                serving.name, receiving.name, teamOneScore, teamTwoScore, games.id, round
                                FROM games 
                                INNER JOIN teams serving ON games.teamOne = serving.id
                                INNER JOIN teams receiving ON games.teamTwo = receiving.id
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
                                serving.name, receiving.name, teamOneScore, teamTwoScore, games.id, round
                                FROM games 
                                INNER JOIN teams AS serving ON games.teamOne = serving.id 
                                INNER JOIN teams AS receiving ON games.teamTwo = receiving.id
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
                        serving.name, receiving.name, teamOneScore, teamTwoScore, games.id, 
                        umpire.name, umpire.searchableName, scorer.name, scorer.searchableName, 
                        court, round
                        FROM games 
                        INNER JOIN teams AS serving ON games.teamOne = serving.id 
                        INNER JOIN teams AS receiving ON games.teamTwo = receiving.id
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
                        serving.name, receiving.name, teamOneScore, teamTwoScore, games.id, 
                        umpire.name, umpire.searchableName, scorer.name, scorer.searchableName, 
                        court, round
                        FROM games 
                        INNER JOIN teams AS serving ON games.teamOne = serving.id 
                        INNER JOIN teams AS receiving ON games.teamTwo = receiving.id
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
                                            then '/api/teams/image?name=blank' 
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
                """
                        SELECT teams.name,
       teams.searchableName,
       case 
            when teams.imageURL is null 
                then '/api/teams/image?name=blank' 
            else 
                teams.imageURL
            end,
       ROUND(1500.0 + (SELECT SUM(eloChange)
                       from eloChange
                                INNER JOIN teams inside ON inside.id = teams.id
                                INNER JOIN people captain ON captain.id = inside.captain
                                LEFT JOIN people nonCaptain ON nonCaptain.id = inside.nonCaptain
                                LEFT JOIN people sub ON sub.id = inside.substitute
                       where eloChange.playerId = sub.id
                          or eloChange.playerId = captain.id
                          or eloChange.playerId = nonCaptain.id)
           /
                      COUNT(DISTINCT playerGameStats.playerId), 2) as elo,
       tournamentTeams.gamesPlayed,
       tournamentTeams.gamesWon,
       tournamentTeams.gamesLost,
       ROUND(100.0 * Cast(tournamentTeams.gamesWon AS REAL) / tournamentTeams.gamesPlayed,
             2) || '%',
       SUM(playerGameStats.greenCards),
       SUM(playerGameStats.yellowCards),
       SUM(playerGameStats.redCards),
       SUM(playerGameStats.faults),
       tournamentTeams.timeoutsCalled,
       SUM(playerGameStats.points),
       (SELECT SUM(playerGameStats.points)
            FROM playerGameStats
            where playerGameStats.opponentId = teams.id and playerGameStats.tournamentId = tournaments.id),
       SUM(playerGameStats.points) - (SELECT SUM(playerGameStats.points)
                            FROM playerGameStats
                            where playerGameStats.opponentId = teams.id and playerGameStats.tournamentId = tournaments.id) 
FROM teams
         INNER JOIN tournaments on tournaments.searchableName = ?
         INNER JOIN tournamentTeams ON teams.id = tournamentTeams.teamId and tournamentTeams.tournamentId = tournaments.id
         INNER JOIN playerGameStats
                    ON teams.id = playerGameStats.teamId AND playerGameStats.tournamentId = tournaments.id
         
where teams.searchableName = ?
;""",
                (tournament, team_name,),
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
                """
                        SELECT people.name,
       people.searchableName,
       SUM(playerGameStats.isBestPlayer),
       ROUND(1500.0 + (SELECT SUM(eloChange)
                       from eloChange
                       where eloChange.playerId = people.id), 2) as elo,
       SUM(playerGameStats.points),
       SUM(playerGameStats.aces),
       SUM(playerGameStats.faults),
       SUM(playerGameStats.doubleFaults),
       SUM(playerGameStats.greenCards),
       SUM(playerGameStats.yellowCards),
       SUM(playerGameStats.redCards),
       SUM(playerGameStats.roundsPlayed),
       SUM(playerGameStats.roundsBenched),
       ROUND((SELECT SUM(eloChange)
                       from eloChange
                       INNER JOIN games on eloChange.gameId = games.id
                       where eloChange.playerId = people.id AND games.tournamentId = tournaments.id), 2),
       ROUND((SELECT SUM(eloChange)                       from eloChange
                       INNER JOIN games on eloChange.gameId = games.id
                       where eloChange.playerId = people.id AND games.tournamentId = tournaments.id) / COUNT(DISTINCT playerGameStats.gameId), 2) as elo,
       SUM(playerGameStats.servedPoints),
       ROUND(CAST(SUM(playerGameStats.points) AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 2),
       ROUND(CAST(SUM(playerGameStats.points) AS REAL) / (COUNT(DISTINCT playerGameStats.gameId) - tournamentTeams.gamesWon), 2),
       ROUND(CAST(SUM(playerGameStats.aces) AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 2),
       ROUND(CAST(SUM(playerGameStats.faults) AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 2),
       ROUND(CAST(SUM(playerGameStats.greenCards + playerGameStats.yellowCards + playerGameStats.redCards) AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 2),
       SUM(playerGameStats.greenCards + playerGameStats.yellowCards + playerGameStats.redCards),
       ROUND(CAST(SUM(playerGameStats.points) AS REAL) / (SUM(playerGameStats.greenCards + playerGameStats.yellowCards + playerGameStats.redCards)), 2),
       ROUND(CAST(SUM(playerGameStats.servedPoints) AS REAL) / (SUM(playerGameStats.aces)), 2),
       ROUND(CAST(SUM(playerGameStats.servedPoints) AS REAL) / (SUM(playerGameStats.faults)), 2),
       ROUND(CAST(100.0 * SUM(playerGameStats.aces) AS REAL) / (SUM(playerGameStats.servedPoints)), 2)|| '%',
       ROUND(CAST(100.0 * SUM(playerGameStats.faults) AS REAL) / (SUM(playerGameStats.servedPoints)), 2)|| '%',
       ROUND(CAST(100.0 * SUM(playerGameStats.points) AS REAL) / (SUM(playerGameStats.roundsPlayed + playerGameStats.roundsBenched)), 2)|| '%',
       ROUND(CAST(100.0 * SUM(playerGameStats.points) AS REAL) / (SELECT SUM(i.points) from playerGameStats i where i.teamId = teams.id and i.tournamentId = tournaments.id ), 2)|| '%',
       ROUND(CAST(100.0 * SUM(playerGameStats.sideOfCourt = 'Left') AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 2)|| '%',
       ROUND(CAST(100.0 * SUM(playerGameStats.servedPointsWon) AS REAL) / SUM(playerGameStats.servedPoints), 2)|| '%',
       SUM(playerGameStats.servesReturned),
       SUM(playerGameStats.servesReceived),
       ROUND(CAST(100.0 * SUM(playerGameStats.servesReturned) AS REAL) / SUM(playerGameStats.servesReceived), 2) || '%',
       ROUND(CAST(100.0 * SUM(playerGameStats.isBestPlayer) AS REAL) / COUNT( DISTINCT playerGameStats.gameId), 2)
       
       
FROM teams
         INNER JOIN tournaments on tournaments.searchableName = ?
         INNER JOIN tournamentTeams on teams.id = tournamentTeams.teamId and tournaments.id = tournamentTeams.tournamentId 
         INNER JOIN playerGameStats on teams.id = playerGameStats.teamId and playerGameStats.tournamentId = tournaments.id
         INNER JOIN people on playerGameStats.playerId = people.id
         INNER JOIN games on playerGameStats.gameId = games.id
         WHERE teams.searchableName = ? and games.isBye = 0 and games.isFinal = 0
          GROUP BY people.name""",
                (tournament, team_name),
            ).fetchall()
            recent = c.execute(
                """ SELECT s.name, r.name, g1.teamOneScore, g1.teamTwoScore, g1.id, tournaments.searchableName
                    FROM games g1
                             INNER JOIN tournaments on g1.tournamentId = tournaments.id
                             INNER JOIN teams r on g1.teamTwo = r.id
                             INNER JOIN teams s on g1.teamOne = s.id
                    WHERE (r.searchableName = ? or s.searchableName = ?) and tournaments.searchableName = ? and g1.started = 1
                    ORDER BY g1.id DESC 
                    LIMIT 20""", (team_name, team_name, tournament)).fetchall()
            upcoming = c.execute(
                """ SELECT s.name, r.name, g1.teamOneScore, g1.teamTwoScore, g1.id, tournaments.searchableName
                    FROM games g1
                             INNER JOIN tournaments on g1.tournamentId = tournaments.id
                             INNER JOIN teams r on g1.teamTwo = r.id
                             INNER JOIN teams s on g1.teamOne = s.id
                    WHERE (r.searchableName = ? or s.searchableName = ?) and tournaments.searchableName = ? and g1.started = 0
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
                                       round(SUM(eloChange.eloChange) + 1500, 2) as elo,
                                       case 
                                        when round((SELECT eloChange
                                        from eloChange
                                        where eloChange.playerId = playerGameStats.playerId
                                          and eloChange.gameId = games.id), 2) is null 
                                            then 0 
                                        else 
                                            round((SELECT eloChange
                                        from eloChange
                                        where eloChange.playerId = playerGameStats.playerId
                                          and eloChange.gameId = games.id), 2)
                                        end as eloDelta,
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
                                       games.teamOne = teams.id,
                                       games.teamOneScore,
                                       games.teamTwoScore,
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
                                       case 
                                        when teams.imageURL is null 
                                            then '/api/teams/image?name=blank' 
                                        else 
                                            teams.imageURL
                                        end,
                                       people.searchableName,
                                       games.status,
                                       games.gameString, --35
                                       games.teamOneTimeouts,
                                       games.teamTwoTimeouts
                
                                FROM games
                                         INNER JOIN playerGameStats on playerGameStats.gameId = games.id
                                         INNER JOIN tournaments on tournaments.id = games.tournamentId
                                         LEFT JOIN officials o on o.id = games.official
                                         LEFT JOIN people po on po.id = o.personId
                                         LEFT JOIN officials s on s.id = games.scorer
                                         LEFT JOIN people ps on ps.id = s.personId
                                         INNER JOIN people on people.id = playerGameStats.playerId
                                         LEFT JOIN people best on best.id = games.bestPlayer
                                         INNER JOIN teams on teams.id = playerGameStats.teamId
                                         INNER JOIN eloChange on games.id >= eloChange.gameId and eloChange.playerId = playerGameStats.playerId
                                WHERE games.id = ?
                                GROUP BY people.name
                                order by teams.id = games.teamOne, playerGameStats.sideOfCourt;""",
                (game_id,),
            ).fetchall()
            other_matches = c.execute(
                """ SELECT s.name, r.name, g2.teamOneScore, g2.teamTwoScore, g2.id, tournaments.searchableName
                    FROM games g1
                             INNER JOIN games g2
                                        ON ((g2.teamOne = g1.teamOne AND g2.teamTwo = g1.teamTwo)
                                            OR (g2.teamOne = g1.teamTwo AND g2.teamTwo = g1.teamOne))
                                            AND g1.id <> g2.id --funny != symbol lol
                             INNER JOIN tournaments on g2.tournamentId = tournaments.id
                             INNER JOIN teams r on g2.teamTwo = r.id
                             INNER JOIN teams s on g2.teamOne = s.id
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
                team.stats["Timeouts Remaining"] = 1 - players[0][37]
            else:
                team.stats["Timeouts Remaining"] = 1 - players[0][36]

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
        print(players)
        return (
            render_template_sidebar(
                "tournament_specific/game_page.html",
                game=game,
                teams=teams,
                best=best,
                team_headings=team_headers,
                player_headings=player_headers,
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

        @dataclass
        class Team:
            name: str
            searchableName: str
            pool: int
            image: str
            stats: dict[str, object]

        with DatabaseManager() as c:
            teams = c.execute(
                """SELECT tournaments.isPooled,
                       teams.searchableName,
                       teams.name,
                       case
                           when teams.imageURL is null
                               then '/api/teams/image?name=blank'
                           else
                               teams.imageURL
                           end,
                       tournamentTeams.pool,
                       tournamentTeams.gamesPlayed                                                                           as played,
                       tournamentTeams.gamesWon                                                                              as wins,
                       ROUND(100.0 * Cast(tournamentTeams.gamesWon AS REAL) / tournamentTeams.gamesPlayed,
                             2)|| '%'                                                                                              as percentage,
                       tournamentTeams.gamesLost                                                                             as losses,
                       SUM(playerGameStats.greenCards)                                                                       as greenCards,
                       SUM(playerGameStats.yellowCards)                                                                      as yellowCards,
                       SUM(playerGameStats.redCards)                                                                         as redCards,
                       SUM(playerGameStats.faults)                                                                           as faults,
                       tournamentTeams.timeoutsCalled                                                                        as timeouts,
                       SUM(playerGameStats.points)                                                                           as pointsScored,
                       (SELECT SUM(playerGameStats.points)
                            FROM playerGameStats
                            where playerGameStats.opponentId = teams.id and playerGameStats.tournamentId = tournaments.id)                                                    as pointsConceded,
                       SUM(playerGameStats.points) - (SELECT SUM(playerGameStats.points)
                            FROM playerGameStats
                            where playerGameStats.opponentId = teams.id and playerGameStats.tournamentId = tournaments.id)                       as difference,
                       ROUND(1500.0 + (SELECT SUM(eloChange)
                                       from eloChange
                                                INNER JOIN teams inside ON inside.id = teams.id
                                                INNER JOIN people captain ON captain.id = inside.captain
                                                LEFT JOIN people nonCaptain ON nonCaptain.id = inside.nonCaptain
                                                LEFT JOIN people sub ON sub.id = inside.substitute
                                       where eloChange.playerId = sub.id
                                          or eloChange.playerId = captain.id
                                          or eloChange.playerId = nonCaptain.id)
                           /
                                      COUNT(DISTINCT playerGameStats.playerId), 2)                                           as elo
                
                FROM tournamentTeams
                         INNER JOIN tournaments ON tournaments.id = tournamentTeams.tournamentId
                         INNER JOIN teams ON teams.id = tournamentTeams.teamId
                         INNER JOIN playerGameStats
                                    ON teams.id = playerGameStats.teamId AND playerGameStats.tournamentId = tournaments.id
                WHERE tournaments.searchableName = ?
                GROUP BY teams.name
                ORDER BY percentage DESC,
                         difference DESC,
                         pointsScored DESC,
                         greenCards + yellowCards + redCards ASC,
                         redCards ASC,
                         yellowCards ASC,
                         faults ASC,
                         SUM(timeoutsCalled) ASC""",
                (tournament,),
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
        player_headers = ["B&F Votes",
                          "Games Won",
                          "Games Lost",
                          "Games Played",
                          "Percentage",
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
                        teams.searchableName,
       SUM(playerGameStats.isBestPlayer),
       SUM(games.winningTeam = playerGameStats.teamId),
       SUM(games.winningTeam <> playerGameStats.teamId),
       COUNT(DISTINCT games.id),
       ROUND(100.0 * SUM(CAST(games.winningTeam = playerGameStats.teamId AS REAL)) / COUNT(DISTINCT games.id), 2)|| '%',
       ROUND(1500.0 + (SELECT SUM(eloChange)
                       from eloChange
                       where eloChange.playerId = people.id), 2) as elo,
       SUM(playerGameStats.points),
       SUM(playerGameStats.aces),
       SUM(playerGameStats.faults),
       SUM(playerGameStats.doubleFaults),
       SUM(playerGameStats.greenCards),
       SUM(playerGameStats.yellowCards),
       SUM(playerGameStats.redCards),
       SUM(playerGameStats.roundsPlayed),
       SUM(playerGameStats.roundsBenched),
       ROUND((SELECT SUM(eloChange)
              from eloChange
                       INNER JOIN games on eloChange.gameId = games.id
              where eloChange.playerId = people.id AND games.tournamentId = tournaments.id), 2),
       ROUND((SELECT SUM(eloChange)                       from eloChange
                                                                   INNER JOIN games on eloChange.gameId = games.id
              where eloChange.playerId = people.id AND games.tournamentId = tournaments.id) / COUNT(DISTINCT playerGameStats.gameId), 2) as elo,
       SUM(playerGameStats.servedPoints),
       ROUND(CAST(SUM(playerGameStats.points) AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 2),
       ROUND(CAST(SUM(playerGameStats.points) AS REAL) / tournamentTeams.gamesLost, 2),
       ROUND(CAST(SUM(playerGameStats.aces) AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 2),
       ROUND(CAST(SUM(playerGameStats.faults) AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 2),
       ROUND(CAST(SUM(playerGameStats.greenCards + playerGameStats.yellowCards + playerGameStats.redCards) AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 2),
       SUM(playerGameStats.greenCards + playerGameStats.yellowCards + playerGameStats.redCards),
       ROUND(CAST(SUM(playerGameStats.points) AS REAL) / (SUM(playerGameStats.greenCards + playerGameStats.yellowCards + playerGameStats.redCards)), 2),
       ROUND(CAST(SUM(playerGameStats.servedPoints) AS REAL) / (SUM(playerGameStats.aces)), 2),
       ROUND(CAST(SUM(playerGameStats.servedPoints) AS REAL) / (SUM(playerGameStats.faults)), 2),
       ROUND(CAST(100.0 * SUM(playerGameStats.aces) AS REAL) / (SUM(playerGameStats.servedPoints)), 2)|| '%',
       ROUND(CAST(100.0 * SUM(playerGameStats.faults) AS REAL) / (SUM(playerGameStats.servedPoints)), 2)|| '%',
       ROUND(CAST(100.0 * SUM(playerGameStats.points) AS REAL) / (SUM(playerGameStats.roundsPlayed + playerGameStats.roundsBenched)), 2)|| '%',
       ROUND(CAST(100.0 * SUM(playerGameStats.points) AS REAL) / (SELECT SUM(i.points) from playerGameStats i where i.teamId = teams.id and i.tournamentId = tournaments.id ), 2)|| '%',
       ROUND(CAST(100.0 * SUM(playerGameStats.sideOfCourt = 'Left') AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 2)|| '%',
       ROUND(CAST(100.0 * SUM(playerGameStats.servedPointsWon) AS REAL) / SUM(playerGameStats.servedPoints), 2)|| '%',
       SUM(playerGameStats.servesReturned),
       SUM(playerGameStats.servesReceived),
       ROUND(CAST(100.0 * SUM(playerGameStats.servesReturned) AS REAL) / SUM(playerGameStats.servesReceived), 2) || '%',
       ROUND(CAST(100.0 * SUM(playerGameStats.isBestPlayer) AS REAL) / COUNT( DISTINCT playerGameStats.gameId), 2)

FROM people
         INNER JOIN playerGameStats on people.id = playerGameStats.playerId
         INNER JOIN teams on playerGameStats.teamId = teams.id
         INNER JOIN tournaments on tournaments.id = playerGameStats.tournamentId
         INNER JOIN tournamentTeams on tournaments.id = tournamentTeams.tournamentId and teams.id = tournamentTeams.teamId
         INNER JOIN games on playerGameStats.gameId = games.id
WHERE people.searchableName = ? and games.isBye = 0 and games.isFinal = 0 and tournaments.searchableName = ?""",
                (player_name, tournament), ).fetchone()

            courts = c.execute(
                """SELECT people.name,
                        teams.searchableName,
       SUM(playerGameStats.isBestPlayer),
       SUM(games.winningTeam = playerGameStats.teamId),
       SUM(games.winningTeam <> playerGameStats.teamId),
       COUNT(DISTINCT games.id),
       ROUND(100.0 * SUM(CAST(games.winningTeam = playerGameStats.teamId AS REAL)) / COUNT(DISTINCT games.id), 2)|| '%',
       ROUND(1500.0 + (SELECT SUM(eloChange)
                       from eloChange
                       where eloChange.playerId = people.id), 2) as elo,
       SUM(playerGameStats.points),
       SUM(playerGameStats.aces),
       SUM(playerGameStats.faults),
       SUM(playerGameStats.doubleFaults),
       SUM(playerGameStats.greenCards),
       SUM(playerGameStats.yellowCards),
       SUM(playerGameStats.redCards),
       SUM(playerGameStats.roundsPlayed),
       SUM(playerGameStats.roundsBenched),
       ROUND((SELECT SUM(eloChange)
              from eloChange
                       INNER JOIN games on eloChange.gameId = games.id
              where eloChange.playerId = people.id AND games.tournamentId = tournaments.id), 2),
       ROUND((SELECT SUM(eloChange)                       from eloChange
                                                                   INNER JOIN games on eloChange.gameId = games.id
              where eloChange.playerId = people.id AND games.tournamentId = tournaments.id) / COUNT(DISTINCT playerGameStats.gameId), 2) as elo,
       SUM(playerGameStats.servedPoints),
       ROUND(CAST(SUM(playerGameStats.points) AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 2),
       ROUND(CAST(SUM(playerGameStats.points) AS REAL) / tournamentTeams.gamesLost, 2),
       ROUND(CAST(SUM(playerGameStats.aces) AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 2),
       ROUND(CAST(SUM(playerGameStats.faults) AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 2),
       ROUND(CAST(SUM(playerGameStats.greenCards + playerGameStats.yellowCards + playerGameStats.redCards) AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 2),
       SUM(playerGameStats.greenCards + playerGameStats.yellowCards + playerGameStats.redCards),
       ROUND(CAST(SUM(playerGameStats.points) AS REAL) / (SUM(playerGameStats.greenCards + playerGameStats.yellowCards + playerGameStats.redCards)), 2),
       ROUND(CAST(SUM(playerGameStats.servedPoints) AS REAL) / (SUM(playerGameStats.aces)), 2),
       ROUND(CAST(SUM(playerGameStats.servedPoints) AS REAL) / (SUM(playerGameStats.faults)), 2),
       ROUND(CAST(100.0 * SUM(playerGameStats.aces) AS REAL) / (SUM(playerGameStats.servedPoints)), 2)|| '%',
       ROUND(CAST(100.0 * SUM(playerGameStats.faults) AS REAL) / (SUM(playerGameStats.servedPoints)), 2)|| '%',
       ROUND(CAST(100.0 * SUM(playerGameStats.points) AS REAL) / (SUM(playerGameStats.roundsPlayed + playerGameStats.roundsBenched)), 2)|| '%',
       ROUND(CAST(100.0 * SUM(playerGameStats.points) AS REAL) / (SELECT SUM(i.points) from playerGameStats i where i.teamId = teams.id and i.tournamentId = tournaments.id ), 2)|| '%',
       ROUND(CAST(100.0 * SUM(playerGameStats.sideOfCourt = 'Left') AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 2)|| '%',
       ROUND(CAST(100.0 * SUM(playerGameStats.servedPointsWon) AS REAL) / SUM(playerGameStats.servedPoints), 2)|| '%',
       SUM(playerGameStats.servesReturned),
       SUM(playerGameStats.servesReceived),
       ROUND(CAST(100.0 * SUM(playerGameStats.servesReturned) AS REAL) / SUM(playerGameStats.servesReceived), 2) || '%',
       ROUND(CAST(100.0 * SUM(playerGameStats.isBestPlayer) AS REAL) / COUNT( DISTINCT playerGameStats.gameId), 2)

FROM people
         INNER JOIN playerGameStats on people.id = playerGameStats.playerId
         INNER JOIN teams on playerGameStats.teamId = teams.id
         INNER JOIN tournaments on tournaments.id = playerGameStats.tournamentId
         INNER JOIN tournamentTeams on tournaments.id = tournamentTeams.tournamentId and teams.id = tournamentTeams.teamId
         INNER JOIN games on playerGameStats.gameId = games.id
WHERE people.searchableName = ? and games.isBye = 0 and games.isFinal = 0 and tournaments.searchableName = ?
GROUP BY games.court""",
                (player_name, tournament), ).fetchall()

            recent = c.execute(
                """ SELECT s.name, r.name, g1.teamOneScore, g1.teamTwoScore, g1.id, tournaments.searchableName
                    FROM games g1
                             INNER JOIN tournaments on g1.tournamentId = tournaments.id
                             INNER JOIN teams r on g1.teamTwo = r.id
                             INNER JOIN teams s on g1.teamOne = s.id
                             INNER JOIN playerGameStats on g1.id = playerGameStats.gameId
                             INNER JOIN people on playerGameStats.playerId = people.id
                    WHERE (people.searchableName = ?) and tournaments.searchableName = ? and g1.started = 1
                    ORDER BY g1.id DESC 
                    LIMIT 20""", (player_name, tournament)).fetchall()
            upcoming = c.execute(
                """ SELECT s.name, r.name, g1.teamOneScore, g1.teamTwoScore, g1.id, tournaments.searchableName
                    FROM games g1
                             INNER JOIN tournaments on g1.tournamentId = tournaments.id
                             INNER JOIN teams r on g1.teamTwo = r.id
                             INNER JOIN teams s on g1.teamOne = s.id
                             INNER JOIN playerGameStats on g1.id = playerGameStats.gameId
                             INNER JOIN people on playerGameStats.playerId = people.id
                    WHERE people.searchableName = ? and tournaments.searchableName = ? and g1.started = 0
                    ORDER BY g1.id DESC 
                    LIMIT 20""", (player_name, tournament)).fetchall()
        recent = [
            (f"{i[0]} vs {i[1]} [{i[2]} - {i[3]}]", i[4], i[5]) for i in recent
        ]
        upcoming = [
            (f"{i[0]} vs {i[1]} [{i[2]} - {i[3]}]", i[4], i[5]) for i in upcoming
        ]

        stats = {}
        for k, v in zip(player_headers, players[2:]):
            stats[k] = v
        stats |= {
            f"Court {i + 1}": {k: v for k, v in zip(player_headers, j[2:])} for i, j in enumerate(courts)
        }

        print(stats)
        if user_on_mobile() or True:
            return (
                render_template_sidebar(
                    "tournament_specific/player_stats.html",
                    stats=stats,
                    name=players[0],
                    player=player_name,
                    team=players[1],
                    recent_games=recent,
                    upcoming_games=upcoming,
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
                        for k, v in zip(player_headers, players[2:])
                    ],
                    name=players[0],
                    team=players[1],
                    player=player_name,
                    recent_games=recent,
                    upcoming_games=upcoming,
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
                                   SUM(punishments.type = 'Green'),
                                   SUM(punishments.type = 'Yellow'),
                                   SUM(punishments.type = 'Red'),
                                   COUNT(punishments.reason),
                                   ROUND(CAST(COUNT(punishments.reason) AS REAL) / COUNT(DISTINCT games.id), 2),
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
                                   SUM((SELECT teamOneScore + teamTwoScore FROM games WHERE games.official = officials.id))
                            
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
                teamOneScore,
                teamTwoScore
            FROM games
                     INNER JOIN officials o on games.official = o.id
                     INNER JOIN tournaments on games.tournamentId = tournaments.id
                     LEFT JOIN teams st on st.id = games.teamOne
                     LEFT JOIN teams rt on rt.id = games.teamTwo
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
        visual_swap = request.args.get("swap", "false") == "true"
        visual_str = "true" if visual_swap else "false"

        with DatabaseManager() as c:
            game_query = c.execute("""
SELECT games.tournamentId,
       isBye,
       po.name,
       po.searchableName,
       ps.name,
       ps.searchableName,
       started,
       someoneHasWon,
       tournaments.imageURL,
       gameEvents.eventType = 'Fault',
       server.name,
       lastGe.nextServeSide,
       ended
FROM games
         INNER JOIN tournaments ON games.tournamentId = tournaments.id
         INNER JOIN officials o ON games.official = o.id
         INNER JOIN people po ON o.personId = po.id
         LEFT JOIN officials s ON games.scorer = o.id
         LEFT JOIN people ps ON s.personId = ps.id
         LEFT JOIN gameEvents ON games.id = gameEvents.gameId AND gameEvents.id =
                                                                  (SELECT MAX(id)
                                                                   FROM gameEvents
                                                                   WHERE games.id = gameEvents.gameId
                                                                     AND (gameEvents.eventType = 'Fault' or gameEvents.eventType = 'Score'))
         LEFT JOIN gameEvents lastGE ON games.id = lastGE.gameId AND lastGE.id =
                                                                     (SELECT MAX(id)
                                                                      FROM gameEvents
                                                                      WHERE games.id = gameEvents.gameId)
         LEFT JOIN people server on lastGE.nextPlayerToServe = server.id
WHERE games.id = ?
            """, (game_id,)).fetchone()

            teams_query = c.execute("""SELECT teams.id, teams.name,
       teams.searchableName,
       teams.id <> games.teamOne,
       Case
           WHEN games.teamTwo = teams.id THEN
               games.teamTwoScore
           ELSE
               games.teamOneScore END,
       case
           when teams.imageURL is null
               then '/api/teams/image?name=blank'
           else
               teams.imageURL
           end,
        teams.id = games.teamToServe,
        IIF(sum(playerGameStats.redCards) > 0, -1, max(playerGameStats.cardTimeRemaining)),
        max(IIF(playerGameStats.cardTime is null, 0, playerGameStats.cardTime)),
        max(playerGameStats.greenCards) > 0,
        Case
           WHEN games.teamTwo = teams.id THEN
               games.teamTwoTimeouts
           ELSE
               games.teamOneTimeouts END
FROM games
         INNER JOIN tournaments on games.tournamentId = tournaments.id
         INNER JOIN teams on (games.teamTwo = teams.id or games.teamOne = teams.id)
         INNER JOIN playerGameStats on playerGameStats.teamId = teams.id AND playerGameStats.gameId = games.id 
                    WHERE games.id = ?
                    GROUP BY teams.id
ORDER BY teams.id <> games.teamOne
""", (game_id,)).fetchall()
            players_query = c.execute("""SELECT 
            playerGameStats.teamId, people.name, people.searchableName, playerGameStats.cardTimeRemaining <> 0,
            playerGameStats.points,
            playerGameStats.aces,
            playerGameStats.faults,      
            playerGameStats.doubleFaults,
            playerGameStats.roundsPlayed,
            playerGameStats.roundsBenched,
            playerGameStats.greenCards,
            playerGameStats.yellowCards, 
            playerGameStats.redCards
FROM games
         INNER JOIN playerGameStats on games.id = playerGameStats.gameId
         INNER JOIN people on people.id = playerGameStats.playerId
         WHERE gameId = ?
""", (game_id,)).fetchall()
            cards_query = c.execute("""SELECT people.name, playerGameStats.teamId, type, reason, hex 
            FROM punishments 
            INNER JOIN people on people.id = punishments.playerId
            INNER JOIN playerGameStats on playerGameStats.playerId = punishments.playerId and playerGameStats.gameId = ?
         WHERE playerGameStats.tournamentId = punishments.tournamentId
""", (game_id,)).fetchall()
            officials_query = c.execute("""SELECT searchableName, name 
FROM officials INNER JOIN people on officials.personId = people.id
""").fetchall()
            print(players_query)

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
            deletable: bool

        teams = {}
        cards = [Card(*i) for i in cards_query]
        game = Game(game_id, *game_query[1:], True, False)
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
        team_one_players = [((1 - i), v) for i, v in enumerate(teams[0].players[:2])]
        team_two_players = [((1 - i), v) for i, v in enumerate(teams[1].players[:2])]

        # TODO: Write a permissions decorator for scorers and primary officials
        # if key not in [game.primary_official.key, game.scorer.key] and not is_admin:
        #     return _no_permissions()
        # el
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
                    tournament=link(tournament),
                    swap=visual_str,
                    admin=True,  # key in [i.key for i in get_all_officials() if i.admin]
                ),
                200,
            )
        elif not game.someone_has_won:
            # for i in teams:
            #     i.end_timeout()
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
                    timeout_time=0,
                    timeout_first=0,
                    tournament=link(tournament),
                    match_points=0 if max([i.score for i in teams]) < 10 else abs(teams[0].score - teams[1].score),
                    VERBAL_WARNINGS=VERBAL_WARNINGS
                ),
                200,
            )
        elif game.someone_has_won and not game.ended:
            return (
                render_template(
                    "tournament_specific/game_editor/team_signatures.html",
                    players=[i.name for i in players],
                    swap=visual_str,
                    teams=teams,
                    game=game,
                    headers=player_headers,
                    stats=None,
                    tournament=link(tournament),
                ),
                200,
            )
        elif not game.ended or key in [
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
