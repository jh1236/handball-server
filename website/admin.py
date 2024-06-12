import json
import time
from collections import defaultdict
from dataclasses import dataclass

from flask import render_template

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
from website.website import sign


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
                                       games.length,
                                       games.notes
                
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
                                order by teams.id <> games.teamOne, playerGameStats.sideOfCourt;""",
                (game_id,),
            ).fetchall()
            cards_query = c.execute("""SELECT people.name, playerGameStats.teamId, type, reason, hex 
            FROM punishments 
            INNER JOIN people on people.id = punishments.playerId
            INNER JOIN playerGameStats on playerGameStats.playerId = punishments.playerId and playerGameStats.teamId = punishments.teamId and playerGameStats.gameId = ?
         WHERE playerGameStats.tournamentId = punishments.tournamentId
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
        team = [i for i in comps[tournament].teams if team_name == i.nice_name()][0]
        recent_games = []
        key_matches = []
        for i in comps[tournament].games_to_list():
            if team not in [j.team for j in i.teams] or i.bye:
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
                if i.is_noteable or gt.yellow_cards:
                    key_matches.append(
                        (
                            i.noteable_string(True),
                            repr(i) + f" ({i.score_string}){s}",
                            i.id,
                            i.tournament.nice_name(),
                        )
                    )

        players = [
            (i.name, i.nice_name(),
             [(k, v) for k, v in get_player_stats(comps[tournament], i, team=team, detail=1).items()])
            for i in team.players
        ]
        return (
            render_template_sidebar(
                "tournament_specific/admin/each_team_stats.html",
                stats=[(k, v) for k, v in team.get_stats().items()],
                team=team,
                recent_games=recent_games,
                key_games=key_matches,
                tournament=f"{tournament}/",
                players=players,
            ),
            200,
        )

    @app.get("/<tournament>/teams/admin")
    @admin_only
    def admin_stats_directory_site(tournament):
        teams = [
            i
            for i in sorted(comps[tournament].teams, key=lambda a: a.nice_name())
            if i.games_played > 0 or len(comps[tournament].teams) < 15
        ]
        return (
            render_template_sidebar(
                "tournament_specific/admin/stats.html",
                teams=teams,
                tournament=f"{tournament}/",
            ),
            200,
        )

    @app.get("/<tournament>/players/admin")
    @admin_only
    def admin_players_site(tournament):
        priority = {
            "Name": 1,
            "Penalty Points": 1,
            "Cards": 1,
            "Green Cards": 2,
            "Yellow Cards": 2,
            "Red Cards": 2,
            "Games Played": 3,
            "Rounds Carded": 3,
            "Faults": 4,
            "Double Faults": 5,
            "Rounds Played": 4,
            "Points Served": 5,
            "Points Per Card": 5,
            "Points Per Loss": 5,
            "Votes Per 100 Games": 5,
            "Games Won": 4,
        }
        players = [
            (
                i.name,
                i.team.nice_name(),
                i.nice_name(),
                [(i.get_stats_detailed()[k], v) for k, v in priority.items() if not k == "Name"],
            )
            for i in comps[tournament].players
            if (i.get_stats()["Games Played"] or len(comps[tournament].fixtures) < 2)
               and not i.nice_name().startswith("null")
        ]
        headers = [
            i for i in priority.keys()
        ]
        return (
            render_template_sidebar(
                "tournament_specific/admin/players.html",
                headers=[(i - 1, k, priority[k]) for i, k in enumerate(headers)],
                players=sorted(players),
                tournament=f"{tournament}/",
            ),
            200,
        )

    @app.get("/<tournament>/players/<player_name>/admin")
    @admin_only
    def admin_player_stats(tournament, player_name):
        if player_name not in [i.nice_name() for i in comps[tournament].players]:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This is not a real player",
                ),
                400,
            )
        player = [
            i for i in comps[tournament].players if player_name == i.nice_name()
        ][0]
        noteable_games = []
        cards = []
        for i in comps[tournament].games_to_list():
            if player_name not in [j.nice_name() for j in i.playing_players] or i.bye:
                continue
            gt = next(
                t for t in i.teams if player_name in [j.nice_name() for j in t.players]
            )
            gp = next(p for p in gt.players if player_name == p.nice_name())
            op = next(k for k in i.teams if k.nice_name() != gt.nice_name())
            s = " <+0>"
            if gt.elo_delta:
                s = f" <{sign(gp.elo_delta)}{round(abs(gp.elo_delta), 2)}>"
            if i.started:
                for j in i.cards:
                    if j.player.nice_name() == player_name:
                        cards.append((op, i.id, j.color, j.reason.title()))
                if (
                        gp.yellow_cards
                        or gp.red_cards
                        or i.notes.strip()
                        or (
                        i.protested
                        and i.teams[i.protested - 1].nice_name() == gt.nice_name()
                )
                ):
                    noteable_games.append(
                        (
                            i.noteable_string(True),
                            repr(i) + f" ({i.score_string}){s}",
                            i.id,
                            i.tournament.nice_name(),
                        )
                    )

        return (
            render_template_sidebar(
                "tournament_specific/admin/player_stats.html",
                stats=[(k, v) for k, v in get_player_stats(comps[tournament], player, detail=2).items()],
                name=player.name,
                player=player,
                cards=cards,
                noteable_games=noteable_games,
                tournament=f"{tournament}/",
            ),
            200,
        )

    @app.get("/<tournament>/admin")
    @admin_only
    def admin_home_page(tournament):
        in_progress = any(
            [not (i.best_player or i.bye) for i in comps[tournament].games_to_list()]
        )
        games_requiring_action = []
        for i in comps[tournament].games_to_list():
            if i.requires_action:
                games_requiring_action.append(i)
        ongoing_games = [
            i for i in comps[tournament].games_to_list() if i.in_progress
        ]
        current_round = fixture_sorter(
            [
                [
                    game
                    for r in comps[tournament].finals
                    for game in r
                    if not game.super_bye
                ]
                if comps[tournament].in_finals
                else comps[tournament].fixtures[-1]
            ]
        )[0]
        if (
                all([i.bye for i in current_round]) and len(comps[tournament].fixtures) > 1
        ):  # basically just for home and aways
            current_round = comps[tournament].fixtures[-2]
        players = comps[tournament].players
        players = [i for i in players if "null" not in i.nice_name()]
        players.sort(key=lambda a: -a.get_stats_detailed()["Penalty Points"])
        if len(players) > 10:
            players = players[0:10]

        return (
            render_template_sidebar(
                "tournament_specific/admin/tournament_home.html",
                tourney=comps[tournament],
                ongoing=ongoing_games,
                current_round=current_round,
                players=players,
                notes=comps[tournament].notes,
                in_progress=in_progress,
                tournament=f"{tournament}/",
                require_action=games_requiring_action,
            ),
            200,
        )
