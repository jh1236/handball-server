import json
import time
from collections import defaultdict
from dataclasses import dataclass

from flask import render_template

from FixtureGenerators.FixturesGenerator import get_type_from_name
from structure.GameUtils import game_string_to_events
from structure.Player import Player
from structure.Team import Team
from structure.Tournament import Tournament
from structure.get_information import get_tournament_id
from utils.databaseManager import DatabaseManager
from utils.permissions import admin_only
from utils.sidebar_wrapper import render_template_sidebar
from utils.statistics import get_player_stats
from utils.util import fixture_sorter
from website.tournament_specific import priority_to_classname
from website.website import sign, numbers


def add_admin_pages(app, comps: dict[str, Tournament]):
    @app.get("/<tournament>/fixtures/admin")
    @admin_only
    def admin_fixtures(tournament):
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
            cards: int
            notes: str
            status: str

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
                        court, round, SUM(playerGameStats.greenCards + playerGameStats.yellowCards + playerGameStats.redCards),
                        games.notes, adminStatus
                        FROM games 
                        INNER JOIN playerGameStats ON playerGameStats.gameId = games.id
                        INNER JOIN teams AS serving ON games.teamOne = serving.id 
                        INNER JOIN teams AS receiving ON games.teamTwo = receiving.id
                        LEFT JOIN officials AS u ON games.official = u.id
                            LEFT JOIN people AS umpire ON u.personId = umpire.id
                        LEFT JOIN officials AS s ON games.scorer = s.id
                            LEFT JOIN people AS scorer ON s.personId = scorer.id
                        WHERE
                            games.tournamentId = ? AND
                            games.isFinal = 0
                        GROUP BY games.id
                            """,
                (tournamentId,),
            )
            fixtures = defaultdict(list)
            for game in games:
                fixtures[game[10]].append(
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
                        game[11],
                        game[12] or '',
                        game[13]
                    )
                )

            games = c.execute(
                """SELECT 
                        serving.name, receiving.name, teamOneScore, teamTwoScore, games.id, 
                        umpire.name, umpire.searchableName, scorer.name, scorer.searchableName, 
                        court, round, SUM(playerGameStats.greenCards + playerGameStats.yellowCards + playerGameStats.redCards),
                        games.notes, adminStatus
                        FROM games 
                        INNER JOIN playerGameStats ON playerGameStats.gameId = games.id
                        INNER JOIN teams AS serving ON games.teamOne = serving.id 
                        INNER JOIN teams AS receiving ON games.teamTwo = receiving.id
                        LEFT JOIN officials AS u ON games.official = u.id
                            LEFT JOIN people AS umpire ON u.personId = umpire.id
                        LEFT JOIN officials AS s ON games.scorer = s.id
                            LEFT JOIN people AS scorer ON s.personId = scorer.id
                        WHERE
                            games.tournamentId = ? AND
                            games.isFinal = 1
                        GROUP BY games.id
                            """,
                (tournamentId,),
            )
            finals = defaultdict(list)
            for game in games:
                finals[game[10]].append(
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
                        game[11],
                        game[12] or '',
                        game[13],
                    )
                )

            t = Tourney(
                *c.execute(
                    """SELECT
                                twoCourts, hasScorer
                                FROM tournaments
                                INNER JOIN games ON games.tournamentId = tournaments.id
                                WHERE tournaments.id = ?;""",
                    (tournamentId,),
                ).fetchone()
            )

        return (
            render_template_sidebar(
                "tournament_specific/admin/site.html",
                fixtures=fixtures.items(),
                finals=finals.items(),
                t=t,
                reset=False,
            ),
            200,
        )

    @app.get("/signup/admin")
    @admin_only
    def admin_sign_up():
        teams = []
        with open("./config/signups/teams.json") as fp:
            teams_raw = json.load(fp)
        for k, v in teams_raw.items():
            t = Team(k, [Player(j) for j in v["players"]])
            t.primary_color = v["colors"][0]
            t.secondary_color = v["colors"][1]
            teams.append(t)
        with open("config/signups/officials.json") as fp:
            umpires = json.load(fp)
        return render_template_sidebar(
            "sign_up/admin.html",
            tournament="Fifth S.U.S.S. Championship",
            teams=teams,
            umpires=umpires,
        )

    @app.get("/games/<game_id>/admin")
    @admin_only
    def admin_game_site(game_id):
        with DatabaseManager() as c:
            players = c.execute(
                """SELECT people.name,
                                       round(coalesce(SUM(eloChange.eloChange) + 1500,0), 2) as elo,
                                       case 
                                        when round(coalesce((SELECT eloChange
                                        from eloChange
                                        where eloChange.playerId = playerGameStats.playerId
                                          and eloChange.gameId = games.id), 0), 2) is null 
                                            then 0 
                                        else 
                                            round(coalesce((SELECT eloChange
                                        from eloChange
                                        where eloChange.playerId = playerGameStats.playerId
                                          and eloChange.gameId = games.id), 0), 2)
                                        end as eloDelta,
                                       coalesce(playerGameStats.points, 0),
                                       coalesce(playerGameStats.aces, 0),
                                       coalesce(playerGameStats.faults, 0), --5
                                       coalesce(playerGameStats.doubleFaults, 0),
                                       coalesce(playerGameStats.roundsPlayed, 0),
                                       coalesce(playerGameStats.roundsBenched, 0),
                                       coalesce(playerGameStats.greenCards, 0),
                                       coalesce(playerGameStats.yellowCards, 0), --10
                                       coalesce(playerGameStats.redCards, 0),
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
                                       coalesce(games.startTime, -1),
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
                                       games.adminStatus,
                                       games.gameString, --35
                                       games.teamOneTimeouts,
                                       games.teamTwoTimeouts,
                                       coalesce(games.length, -1),
                                       coalesce(games.notes, '')
                
                                FROM games
                                         LEFT JOIN playerGameStats on playerGameStats.gameId = games.id
                                         INNER JOIN tournaments on tournaments.id = games.tournamentId
                                         LEFT JOIN officials o on o.id = games.official
                                         LEFT JOIN people po on po.id = o.personId
                                         LEFT JOIN officials s on s.id = games.scorer
                                         LEFT JOIN people ps on ps.id = s.personId
                                         LEFT JOIN people on people.id = playerGameStats.playerId
                                         LEFT JOIN people best on best.id = games.bestPlayer
                                         LEFT JOIN teams on teams.id = playerGameStats.teamId
                                         LEFT JOIN eloChange on games.id >= eloChange.gameId and eloChange.playerId = playerGameStats.playerId
                                WHERE games.id = ?
                                GROUP BY people.name
                                order by teams.id <> games.teamOne, playerGameStats.startSide;""",
                (game_id,),
            ).fetchall()
            cards_query = c.execute("""SELECT people.name, playerGameStats.teamId, type, reason, hex 
            FROM punishments 
            INNER JOIN people on people.id = punishments.playerId
            INNER JOIN playerGameStats on playerGameStats.playerId = punishments.playerId and playerGameStats.gameId = punishments.gameId
         WHERE playerGameStats.gameId = ?
""", (game_id,)).fetchall()
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
        class Card:
            player: str
            team: int
            type: str
            reason: str
            hex: str

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
            length: str
            startTimeStr: str
            status: str
            notes: str
            cards: list
        cards = [Card(*i) for i in cards_query]
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
            "?" if players[0][38] < 0
            else time.strftime("%d/%m/%y (%H:%M)", time.localtime(players[0][38])),
            "?"
            if time_float < 0
            else time.strftime("%d/%m/%y (%H:%M)", time.localtime(time_float)),
            players[0][34],
            players[0][39],
            cards
        )

        best = game.bestSearchableName if game.bestSearchableName else "TBD"

        round_number = game.round
        prev_matches = [
            (f"{i[0]} vs {i[1]} [{i[2]} - {i[3]}]", i[4], i[5]) for i in other_matches
        ]
        prev_matches = prev_matches or [("No other matches", -1, players[0][29])]
        return (
            render_template_sidebar(
                "tournament_specific/admin/game_page.html",
                game=game,
                teams=teams,
                best=best,
                team_headings=team_headers,
                player_headings=player_headers,
                commentary=game_string_to_events(game.id),
                roundNumber=round_number,
                prev_matches=prev_matches,
                tournament=players[0][13],
                tournamentLink=players[0][14] + "/",
            ),
            200,
        )

    @app.get("/<tournament>/teams/<team_name>/admin")
    @admin_only
    def admin_team_site(tournament, team_name):
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
       teams.searchableName,
       case
           when teams.imageURL is null
               then '/api/teams/image?name=blank'
           else
               teams.imageURL
           end,
       ROUND(1500.0 + coalesce((SELECT SUM(eloChange)
                                from eloChange
                                         INNER JOIN teams inside ON inside.id = teams.id
                                         INNER JOIN people captain ON captain.id = inside.captain
                                         LEFT JOIN people nonCaptain ON nonCaptain.id = inside.nonCaptain
                                         LEFT JOIN people sub ON sub.id = inside.substitute
                                where eloChange.playerId = sub.id
                                   or eloChange.playerId = captain.id
                                   or eloChange.playerId = nonCaptain.id AND eloChange.id <=
                                      (SELECT MAX(id) FROM eloChange WHERE eloChange.tournamentId = tournaments.id)), 0)
           /
                      COUNT(teams.captain is not null + teams.noncaptain is not null + teams.substitute is not null),
             2) as elo,
       COUNT(DISTINCT games.id),
       COUNT(DISTINCT IIF(games.winningTeam = teams.id, games.id, NULL)),
       COUNT(DISTINCT playerGameStats.gameId) - COUNT(DISTINCT IIF(games.winningTeam = teams.id, games.id, NULL)),
       ROUND(100.0 * Cast(COUNT(DISTINCT IIF(games.winningTeam = teams.id, games.id, NULL)) AS REAL) /
             COUNT(DISTINCT playerGameStats.gameId),
             2) || '%',
       coalesce(SUM(playerGameStats.greenCards), 0),
       coalesce(SUM(playerGameStats.yellowCards), 0),
       coalesce(SUM(playerGameStats.redCards), 0),
       coalesce(SUM(playerGameStats.faults), 0),
       coalesce(SUM((SELECT IIF(games.teamOne = teams.id, games.teamOneTimeouts, games.teamTwoTimeouts)
                     FROM games
                     WHERE games.id = gameId
                       AND playerId = teams.captain)), 0),
       coalesce(SUM((SELECT IIF(games.teamOne = teams.id, games.teamOneScore, games.teamTwoScore)
                     FROM games
                     WHERE games.id = gameId
                       AND playerId = teams.captain)), 0),
       coalesce(SUM((SELECT IIF(games.teamOne = teams.id, games.teamTwoScore, games.teamOneScore)
                     FROM games
                     WHERE games.id = gameId
                       AND playerId = teams.captain)), 0),
       coalesce(SUM(playerGameStats.points) -
                SUM((SELECT IIF(games.teamOne = teams.id, games.teamTwoScore, games.teamOneScore)
                     FROM games
                     WHERE games.id = gameId
                       AND playerId = teams.captain)), 0)
FROM teams
         INNER JOIN tournamentTeams on teams.id = tournamentTeams.teamId
         LEFT JOIN games ON (games.teamOne = teams.id OR games.teamTwo = teams.id) AND games.isFinal = 0 AND
                            games.isBye = 0 AND (IIF(? is null, games.isRanked, 1) OR teams.nonCaptain is null) AND games.tournamentId = tournamentTeams.tournamentId
         LEFT JOIN playerGameStats ON teams.id = playerGameStats.teamId AND games.id = playerGameStats.gameId
         LEFT JOIN tournaments on tournaments.id = tournamentTeams.tournamentId

where IIF(? is NULL, 1, tournaments.id = ?)
  AND teams.searchableName = ?
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
       people.searchableName,
       coalesce(SUM(playerGameStats.isBestPlayer), 0),
       ROUND(1500.0 + (SELECT SUM(eloChange)
                       from eloChange
                       where eloChange.playerId = people.id AND eloChange.id <=
                                      (SELECT MAX(id) FROM eloChange WHERE eloChange.tournamentId = playerGameStats.tournamentId)), 2) as elo,
       coalesce(SUM(playerGameStats.points), 0),
       coalesce(SUM(playerGameStats.aces), 0),
       coalesce(SUM(playerGameStats.faults), 0),
       coalesce(SUM(playerGameStats.doubleFaults), 0),
       coalesce(SUM(playerGameStats.greenCards), 0),
       coalesce(SUM(playerGameStats.yellowCards), 0),
       coalesce(SUM(playerGameStats.redCards), 0),
       coalesce(SUM(playerGameStats.roundsPlayed), 0),
       coalesce(SUM(playerGameStats.roundsBenched), 0),
       coalesce(ROUND((SELECT SUM(eloChange)
                       from eloChange
                                INNER JOIN games on eloChange.gameId = games.id
                       where eloChange.playerId = people.id
                         AND games.tournamentId = tournamentTeams.tournamentId), 2), 0),
       ROUND(coalesce((SELECT SUM(eloChange)
                       from eloChange
                                INNER JOIN games on eloChange.gameId = games.id
                       where eloChange.playerId = people.id
                         AND games.tournamentId = tournamentTeams.tournamentId), 0) / COUNT(DISTINCT playerGameStats.gameId),
                2)                                               as elo,
       coalesce(SUM(playerGameStats.servedPoints), 0),
       ROUND(coalesce(CAST(SUM(playerGameStats.points) AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.points) AS REAL) / (COUNT(DISTINCT playerGameStats.gameId) -
                                                                   COUNT(DISTINCT IIF(games.winningTeam = teams.id, games.id, NULL))),
                      0),
             2),
       ROUND(coalesce(CAST(SUM(playerGameStats.aces) AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.faults) AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.greenCards + playerGameStats.yellowCards +
                               playerGameStats.redCards) AS REAL) /
                      COUNT(DISTINCT playerGameStats.gameId), 0), 2),
       coalesce(SUM(playerGameStats.greenCards + playerGameStats.yellowCards + playerGameStats.redCards), 0),
       ROUND(coalesce(CAST(SUM(playerGameStats.points) AS REAL) /
                      (SUM(playerGameStats.greenCards + playerGameStats.yellowCards + playerGameStats.redCards)), 0),
             2),
       ROUND(coalesce(CAST(SUM(playerGameStats.servedPoints) AS REAL) / (SUM(playerGameStats.aces)), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.servedPoints) AS REAL) / (SUM(playerGameStats.faults)), 0), 2),
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.aces) AS REAL) / (SUM(playerGameStats.servedPoints)), 0), 2) ||
       '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.faults) AS REAL) / (SUM(playerGameStats.servedPoints)), 0), 2) ||
       '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.points) AS REAL) /
                      (SUM(playerGameStats.roundsPlayed + playerGameStats.roundsBenched)), 0), 2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.points) AS REAL) / (SELECT SUM(i.points)
                                                                           from playerGameStats i
                                                                           where i.teamId = teams.id
                                                                             and i.tournamentId = tournamentTeams.tournamentId),
                      0), 2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.startSide = 'Left') AS REAL) /
                      COUNT(DISTINCT playerGameStats.gameId), 0),
             2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.servedPointsWon) AS REAL) / SUM(playerGameStats.servedPoints),
                      0), 2) || '%',
       coalesce(SUM(playerGameStats.servesReceived), 0),
       coalesce(SUM(playerGameStats.servesReturned), 0),
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.servesReturned) AS REAL) / SUM(playerGameStats.servesReceived),
                      0), 2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.isBestPlayer) AS REAL) / COUNT(DISTINCT playerGameStats.gameId),
                      0), 2)


FROM teams
         INNER JOIN tournamentTeams ON teams.id = tournamentTeams.teamId
         INNER JOIN people
                    on (teams.captain = people.id OR teams.noncaptain = people.id OR teams.substitute = people.id)
         LEFT JOIN games on (teams.id = games.teamOne OR   teams.id = teamTwo)
          AND games.tournamentId = tournamentTeams.tournamentId and games.isBye = 0
                                and games.isFinal = 0
                                and (IIF(? is null, games.isRanked, 1) or teams.nonCaptain is null)
         LEFT JOIN playerGameStats on people.id = playerGameStats.playerId AND games.id = playerGameStats.gameId
WHERE teams.searchableName = ?

  and IIF(? is NULL, 1, tournamentTeams.tournamentId = ?)

GROUP BY people.id
ORDER BY people.id <> teams.captain, people.id <> teams.nonCaptain""",
                (tournament_id, team_name, tournament_id, tournament_id),
            ).fetchall()
            cards = c.execute(
                """SELECT type, reason, hex, gameId, people.name
FROM punishments INNER JOIN teams ON teams.id = teamId INNER JOIN people ON playerId = people.id
WHERE teams.searchableName = ?
  AND tournamentId = ?""", (team_name, tournament_id)).fetchall()
            key_games = c.execute(
                """ SELECT s.name, r.name, g1.teamOneScore, g1.teamTwoScore, g1.id, tournaments.searchableName, noteableStatus
                    FROM games g1
                             INNER JOIN tournaments on g1.tournamentId = tournaments.id
                             INNER JOIN teams r on g1.teamTwo = r.id
                             INNER JOIN teams s on g1.teamOne = s.id
                    WHERE (r.searchableName = ? or s.searchableName = ?) and tournaments.searchableName = ? and g1.ended = 1 AND g1.noteableStatus <> 'Official'
                    ORDER BY g1.id DESC 
                    LIMIT 20""", (team_name, team_name, tournament)).fetchall()
        players = [PlayerStats(i[0], i[1], {k: v for k, v in zip(player_headers, i[2:])}) for i in players]
        key_games = [
            (i[6], f"{i[0]} vs {i[1]} [{i[2]} - {i[3]}]", i[4], i[5]) for i in key_games
        ]
        return (
            render_template_sidebar(
                "tournament_specific/admin/each_team_stats.html",
                stats=[(k, v) for k, v in team.stats.items()],
                team=team,
                cards=cards,
                key_games=key_games,
                players=players,
            ),
            200,
        )

    @app.get("/<tournament>/teams/admin")
    @admin_only
    def admin_stats_directory_site(tournament):
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
                                WHERE IIF(? is NULL, 1, tournamentId = ?) GROUP BY teams.id ORDER BY searchableName""",
                (tournamentId, tournamentId),
            ).fetchall()
            teams = [Team(*team) for team in teams]

        return (
            render_template_sidebar(
                "tournament_specific/admin/stats.html",
                teams=teams,
            ),
            200,
        )

    #TODO: complete
    @app.get("/<tournament>/players/admin")
    @admin_only
    def admin_players_site(tournament):
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
                """SELECT teams.imageURL,
       people.searchableName,
       people.name,
       coalesce(SUM(games.bestPlayer = playerId), 0),
       ROUND(1500.0 + coalesce((SELECT SUM(eloChange)
                       from eloChange
                       where eloChange.playerId = people.id AND eloChange.id <=
                                      (SELECT MAX(id) FROM eloChange WHERE eloChange.tournamentId = tournaments.id)), 0), 2) as elo,
       coalesce(SUM(games.winningTeam = playerGameStats.teamId), 0),
       COUNT(DISTINCT games.id),
       coalesce(SUM(playerGameStats.points), 0),
       coalesce(SUM(playerGameStats.aces), 0),
       coalesce(SUM(playerGameStats.faults), 0),
       coalesce(SUM(playerGameStats.doubleFaults), 0),
       coalesce(SUM(playerGameStats.greenCards), 0),
       coalesce(SUM(playerGameStats.yellowCards), 0),
       coalesce(SUM(playerGameStats.redCards), 0),
       coalesce(SUM(playerGameStats.roundsPlayed), 0),
       coalesce(SUM(playerGameStats.servedPoints), 0)

FROM tournamentTeams
         INNER JOIN teams ON teams.id = tournamentTeams.teamId
         INNER JOIN people
                    ON (people.id = teams.captain OR people.id = teams.nonCaptain OR teams.substitute = people.id)
         INNER JOIN tournaments on tournaments.id = tournamentTeams.tournamentId
         LEFT JOIN games
                   on (teams.id = games.teamOne OR teams.id = teamTwo)  AND games.isBye = 0 and games.isFinal = 0 and IIF(? is NULL, games.isRanked, 1) and
                      tournaments.id = games.tournamentId
         LEFT JOIN playerGameStats on games.id = playerGameStats.gameId AND playerId = people.id
         
WHERE IIF(? is NULL, 1, tournaments.id = ?)
GROUP BY people.id""",
                (tournament_id, tournament_id, tournament_id), ).fetchall()

        players = []
        # Im so fucking lazy so im not gonna use a dataclass.  Fucking fight me idec
        for i in players_query:
            players.append(
                (i[2], i[0], i[1], [(v, (priority_to_classname(priority[k]))) for k, v in zip(player_headers, i[3:])]))

        return (
            render_template_sidebar(
                "tournament_specific/admin/players.html",
                headers=[(i - 1, k, priority[k]) for i, k in enumerate(player_headers)],
                players=sorted(players),
            ),
            200,
        )

    @app.get("/<tournament>/players/<player_name>/admin")
    @admin_only
    def admin_player_stats(tournament, player_name):
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
            players = c.execute(
                """SELECT people.name,
       teams.searchableName,
       coalesce(SUM(playerGameStats.isBestPlayer), 0),
       ROUND(1500.0 + (SELECT SUM(eloChange)
                       from eloChange
                       where eloChange.playerId = people.id AND eloChange.id <=
                                      (SELECT MAX(id) FROM eloChange WHERE eloChange.tournamentId = playerGameStats.tournamentId)), 2) as elo,
       coalesce(SUM(winningTeam = teams.id), 0),
       coalesce(SUM(winningTeam <> teams.id), 0),
       COUNT(DISTINCT games.id),
       ROUND(coalesce(100.0 * CAST(SUM(winningTeam = teams.id)  AS REAL) / COUNT(DISTINCT games.id), 0), 2) || '%',
       coalesce(SUM(playerGameStats.points), 0),
       coalesce(SUM(playerGameStats.aces), 0),
       coalesce(SUM(playerGameStats.faults), 0),
       coalesce(SUM(playerGameStats.doubleFaults), 0),
       coalesce(SUM(playerGameStats.greenCards), 0),
       coalesce(SUM(playerGameStats.yellowCards), 0),
       coalesce(SUM(playerGameStats.redCards), 0),
       coalesce(SUM(playerGameStats.roundsPlayed), 0),
       coalesce(SUM(playerGameStats.roundsBenched), 0),
       coalesce(ROUND((SELECT SUM(eloChange)
                       from eloChange
                                INNER JOIN games on eloChange.gameId = games.id
                       where eloChange.playerId = people.id
                         AND games.tournamentId = tournamentTeams.tournamentId), 2), 0),
       ROUND(coalesce((SELECT SUM(eloChange)
                       from eloChange
                                INNER JOIN games on eloChange.gameId = games.id
                       where eloChange.playerId = people.id
                         AND games.tournamentId = tournamentTeams.tournamentId), 0) / COUNT(DISTINCT playerGameStats.gameId),
                2)                                               as elo,
       coalesce(SUM(playerGameStats.servedPoints), 0),
       ROUND(coalesce(CAST(SUM(playerGameStats.points) AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.points) AS REAL) / (COUNT(DISTINCT playerGameStats.gameId) -
                                                                   COUNT(DISTINCT IIF(games.winningTeam = teams.id, games.id, NULL))),
                      0),
             2),
       ROUND(coalesce(CAST(SUM(playerGameStats.aces) AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.faults) AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.greenCards + playerGameStats.yellowCards +
                               playerGameStats.redCards) AS REAL) /
                      COUNT(DISTINCT playerGameStats.gameId), 0), 2),
       coalesce(SUM(playerGameStats.greenCards + playerGameStats.yellowCards + playerGameStats.redCards), 0),
       ROUND(coalesce(CAST(SUM(playerGameStats.points) AS REAL) /
                      (SUM(playerGameStats.greenCards + playerGameStats.yellowCards + playerGameStats.redCards)), 0),
             2),
       ROUND(coalesce(CAST(SUM(playerGameStats.servedPoints) AS REAL) / (SUM(playerGameStats.aces)), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.servedPoints) AS REAL) / (SUM(playerGameStats.faults)), 0), 2),
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.aces) AS REAL) / (SUM(playerGameStats.servedPoints)), 0), 2) ||
       '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.faults) AS REAL) / (SUM(playerGameStats.servedPoints)), 0), 2) ||
       '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.points) AS REAL) /
                      (SUM(playerGameStats.roundsPlayed + playerGameStats.roundsBenched)), 0), 2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.points) AS REAL) / (SELECT SUM(i.points)
                                                                           from playerGameStats i
                                                                           where i.teamId = teams.id
                                                                             and i.tournamentId = tournamentTeams.tournamentId),
                      0), 2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.startSide = 'Left') AS REAL) /
                      COUNT(DISTINCT playerGameStats.gameId), 0),
             2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.servedPointsWon) AS REAL) / SUM(playerGameStats.servedPoints),
                      0), 2) || '%',
       coalesce(SUM(playerGameStats.servesReceived), 0),
       coalesce(SUM(playerGameStats.servesReturned), 0),
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.servesReturned) AS REAL) / SUM(playerGameStats.servesReceived),
                      0), 2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.isBestPlayer) AS REAL) / COUNT(DISTINCT playerGameStats.gameId),
                      0), 2)


FROM teams
         INNER JOIN tournamentTeams ON teams.id = tournamentTeams.teamId
         INNER JOIN people
                    on (teams.captain = people.id OR teams.noncaptain = people.id OR teams.substitute = people.id)
         LEFT JOIN games on (teams.id = games.teamOne OR teams.id = teamTwo)
          AND games.tournamentId = tournamentTeams.tournamentId and games.isBye = 0
                                and games.isFinal = 0
                                and (IIf(? is null, games.isRanked, 1) or teams.nonCaptain is null)
         LEFT JOIN playerGameStats on people.id = playerGameStats.playerId AND games.id = playerGameStats.gameId
WHERE people.searchableName = ?

  and IIF(? is NULL, 1, tournamentTeams.tournamentId = ?)""",
                (tournament_id, player_name, tournament_id, tournament_id), ).fetchone()

            courts = c.execute(
                """SELECT people.name,
       people.searchableName,
       coalesce(SUM(playerGameStats.isBestPlayer), 0),
       ROUND(1500.0 + (SELECT SUM(eloChange)
                       from eloChange
                       where eloChange.playerId = people.id AND eloChange.id <=
                                      (SELECT MAX(id) FROM eloChange WHERE eloChange.tournamentId = playerGameStats.tournamentId)), 2) as elo,
       coalesce(SUM(winningTeam = teams.id), 0),
       coalesce(SUM(winningTeam <> teams.id), 0),
       COUNT(DISTINCT games.id),
       ROUND(coalesce(100.0 * CAST(SUM(winningTeam = teams.id)  AS REAL) / COUNT(DISTINCT games.id), 0), 2) || '%',
       coalesce(SUM(playerGameStats.points), 0),
       coalesce(SUM(playerGameStats.aces), 0),
       coalesce(SUM(playerGameStats.faults), 0),
       coalesce(SUM(playerGameStats.doubleFaults), 0),
       coalesce(SUM(playerGameStats.greenCards), 0),
       coalesce(SUM(playerGameStats.yellowCards), 0),
       coalesce(SUM(playerGameStats.redCards), 0),
       coalesce(SUM(playerGameStats.roundsPlayed), 0),
       coalesce(SUM(playerGameStats.roundsBenched), 0),
       coalesce(ROUND((SELECT SUM(eloChange)
                       from eloChange
                                INNER JOIN games on eloChange.gameId = games.id
                       where eloChange.playerId = people.id
                         AND games.tournamentId = tournamentTeams.tournamentId), 2), 0),
       ROUND(coalesce((SELECT SUM(eloChange)
                       from eloChange
                                INNER JOIN games on eloChange.gameId = games.id
                       where eloChange.playerId = people.id
                         AND games.tournamentId = tournamentTeams.tournamentId), 0) / COUNT(DISTINCT playerGameStats.gameId),
                2)                                               as elo,
       coalesce(SUM(playerGameStats.servedPoints), 0),
       ROUND(coalesce(CAST(SUM(playerGameStats.points) AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.points) AS REAL) / (COUNT(DISTINCT playerGameStats.gameId) -
                                                                   COUNT(DISTINCT IIF(games.winningTeam = teams.id, games.id, NULL))),
                      0),
             2),
       ROUND(coalesce(CAST(SUM(playerGameStats.aces) AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.faults) AS REAL) / COUNT(DISTINCT playerGameStats.gameId), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.greenCards + playerGameStats.yellowCards +
                               playerGameStats.redCards) AS REAL) /
                      COUNT(DISTINCT playerGameStats.gameId), 0), 2),
       coalesce(SUM(playerGameStats.greenCards + playerGameStats.yellowCards + playerGameStats.redCards), 0),
       ROUND(coalesce(CAST(SUM(playerGameStats.points) AS REAL) /
                      (SUM(playerGameStats.greenCards + playerGameStats.yellowCards + playerGameStats.redCards)), 0),
             2),
       ROUND(coalesce(CAST(SUM(playerGameStats.servedPoints) AS REAL) / (SUM(playerGameStats.aces)), 0), 2),
       ROUND(coalesce(CAST(SUM(playerGameStats.servedPoints) AS REAL) / (SUM(playerGameStats.faults)), 0), 2),
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.aces) AS REAL) / (SUM(playerGameStats.servedPoints)), 0), 2) ||
       '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.faults) AS REAL) / (SUM(playerGameStats.servedPoints)), 0), 2) ||
       '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.points) AS REAL) /
                      (SUM(playerGameStats.roundsPlayed + playerGameStats.roundsBenched)), 0), 2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.points) AS REAL) / (SELECT SUM(i.points)
                                                                           from playerGameStats i
                                                                           where i.teamId = teams.id
                                                                             and i.tournamentId = tournamentTeams.tournamentId),
                      0), 2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.startSide = 'Left') AS REAL) /
                      COUNT(DISTINCT playerGameStats.gameId), 0),
             2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.servedPointsWon) AS REAL) / SUM(playerGameStats.servedPoints),
                      0), 2) || '%',
       coalesce(SUM(playerGameStats.servesReceived), 0),
       coalesce(SUM(playerGameStats.servesReturned), 0),
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.servesReturned) AS REAL) / SUM(playerGameStats.servesReceived),
                      0), 2) || '%',
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.isBestPlayer) AS REAL) / COUNT(DISTINCT playerGameStats.gameId),
                      0), 2)


FROM teams
         INNER JOIN tournamentTeams ON teams.id = tournamentTeams.teamId
         INNER JOIN people
                    on (teams.captain = people.id OR teams.noncaptain = people.id OR teams.substitute = people.id)
         LEFT JOIN games on (teams.id = games.teamOne OR teams.id = teamTwo)
          AND games.tournamentId = tournamentTeams.tournamentId and games.isBye = 0
                                and games.isFinal = 0
                                and (iif(? is null, games.isRanked, 1) or teams.nonCaptain is null)
         LEFT JOIN playerGameStats on people.id = playerGameStats.playerId AND games.id = playerGameStats.gameId
WHERE people.searchableName = ?
  and IIF(? is NULL, 1, tournamentTeams.tournamentId = ?) AND court >= 0
  group by games.court""",
                (tournament_id, player_name, tournament_id, tournament_id)).fetchall()

            cards = c.execute(
                """SELECT type, reason, hex, gameId, people.name
FROM punishments INNER JOIN people ON playerId = people.id
WHERE people.searchableName = ?
  AND tournamentId = ?""", (player_name, tournament_id)).fetchall()
            key_games = c.execute(
                """ SELECT s.name, r.name, g1.teamOneScore, g1.teamTwoScore, g1.id, tournaments.searchableName, noteableStatus
                    FROM games g1
                             INNER JOIN tournaments on g1.tournamentId = tournaments.id
                             INNER JOIN teams r on g1.teamTwo = r.id
                             INNER JOIN teams s on g1.teamOne = s.id
                             INNER JOIN playerGameStats on g1.id = playerGameStats.gameId
                             INNER JOIN people on playerGameStats.playerId = people.id
                    WHERE people.searchableName = ? and IIF(? is NULL, 1, tournaments.id = ?) and g1.isBye = 0 AND g1.noteableStatus <> 'Official'
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

        key_games = [
            (i[6], f"{i[0]} vs {i[1]} [{i[2]} - {i[3]}]", i[4], i[5]) for i in key_games
        ]

        stats = {}
        for k, v in zip(player_headers, players[2:]):
            stats[k] = v
        stats |= {
            f"Court {i + 1}": {k: v for k, v in zip(player_headers, j[2:])} for i, j in enumerate(courts)
        }
        return (
            render_template_sidebar(
                "tournament_specific/admin/player_stats.html",
                stats=stats,
                name=players[0],
                player=player_name,
                team=players[1],
                cards = cards,
                key_games=key_games

            ),
            200,
        )

    @app.get("/<tournament>/admin")
    @admin_only
    def admin_home_page(tournament):
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
            pool: int

        @dataclass
        class Game:
            teams: list[str]
            score_string: str
            id: int
            requires_action_string:str = ""

        @dataclass
        class Player:
            name: str
            searchableName: str
            penalty_points: int
            warnings: int
            yellow_cards: int
            red_cards: int
            rounds_on_bench: int

        with DatabaseManager() as c:
            teams = c.execute(
                """
                            SELECT 
                                name, teams.searchableName, gamesWon, gamesPlayed, pool 
                                FROM tournamentTeams 
                                INNER JOIN teams ON tournamentTeams.teamId = teams.id 
                                WHERE tournamentId = ? 
                                ORDER BY 
                                    CAST(gamesWon AS REAL) / tournamentTeams.gamesPlayed DESC 
                                LIMIT 10;""",
                (tournamentId,),
            ).fetchall()
            tourney = c.execute(
                "SELECT name, searchableName, fixturesGenerator, isPooled from tournaments where id = ?",
                (tournamentId,),
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
                                serving.name, receiving.name, teamOneScore, teamTwoScore, games.id, games.adminStatus 
                                FROM games 
                                INNER JOIN teams AS serving ON games.teamOne = serving.id 
                                INNER JOIN teams as receiving ON games.teamTwo = receiving.id 
                                WHERE 
                                    tournamentId = ? AND NOT games.isBye AND (adminStatus <> 'Resolved' AND adminStatus <> 'Official' AND adminStatus <> 'Forfeited');
                            """,
                (tournamentId,),
            ).fetchall()
            games_requiring_action = [
                Game(game[:2], f"{game[2]} - {game[3]}", game[4], game[5]) for game in games
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
                                    people.name, searchableName, sum(yellowCards) * 5 + sum(redCards) * 10, sum(warnings), sum(yellowCards), sum(redCards), sum(roundsBenched) 
                                    FROM playerGameStats 
                                    INNER JOIN people ON playerId = people.id 
                                    WHERE 
                                        tournamentId = ? AND
                                        isFinal = 0
                                    GROUP BY playerId 
                                    ORDER BY 
                                        sum(yellowCards) * 5 + sum(redCards) * 10 DESC 
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
            in_progress = c.execute(
                "SELECT not(isFinished) FROM tournaments WHERE id=?", (tournamentId,)
            ).fetchone()[0]
            iseditable = get_type_from_name(tourney[2], tournamentId).manual_allowed()
            tourney = Tourney(tourney[0], tourney[1], iseditable)
        return (
            render_template_sidebar(
                "tournament_specific/admin/tournament_home.html",
                tourney=tourney,
                current_round=current_round,
                players=players,
                notes=notes,
                in_progress=in_progress,
                require_action=games_requiring_action,
            ),
            200,
        )
