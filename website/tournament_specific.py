import time
from collections import defaultdict
from dataclasses import dataclass

from flask import render_template, request

from Config import Config
from FixtureGenerators.FixturesGenerator import get_type_from_name
from database import db
from database.models import People, PlayerGameStats, Games, Tournaments, TournamentTeams, Teams, TournamentOfficials, \
    Officials, EloChange, GameEvents
from structure import manage_game
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
    @app.get("/<tournament>/")  # TODO: update to use ORM
    def home_page(tournament: str):
        tourney = Tournaments.query.filter(Tournaments.searchable_name == tournament).first()
        if tourney is None:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This is not a real tournament",
                ),
                400,
            )
        tournament_id = tourney.id

        # ladder
        @dataclass
        class LadderTeam:
            name: str
            searchableName: str
            games_won: int
            games_played: int
            pool: int

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
                (tourney.id,),
            ).fetchall()

            ladder = [LadderTeam(*team) for team in teams]

            if tourney.is_pooled:  # this tournament is pooled
                ladder = [
                    (
                        f"Pool {numbers[i]}",
                        list(enumerate((j for j in ladder if j.pool == i), start=1)),
                    )
                    for i in range(1, 3)
                ]
            else:
                ladder = [("", list(enumerate(ladder, start=1)))]

            games = Games.query.filter(Games.tournament_id == tourney.id).all()
            rounds = max(i.round for i in games)
            ongoing_games = [i for i in games if i.round == rounds and not i.ended and not i.is_bye]
            current_round = [i for i in games if (i.round == rounds or i.is_final) and not i.is_bye]

            players = [(i, i.stats()) for i in People.query.order_by().all() if i.played_in_tournament(tournament)]

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
                                        sum(red_cards+yellow_cards+green_cards)  
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
            editable = get_type_from_name(tourney.fixtures_type, tournament_id).manual_allowed()

            return (
                render_template_sidebar(
                    "tournament_specific/tournament_home.html",
                    tourney=tourney,
                    editable=editable,
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
        games = Games.query.filter(Games.tournament_id == tournament_id, Games.is_final == False).all()

        # me when i criticize Jareds code then write this abomination
        fixtures = defaultdict(list)
        for game in games:
            fixtures[game.round].append(game)
        new_fixtures = {}
        for k, v in fixtures.items():
            new_fixtures[k] = [j for j in fixture_sorter(v)]
        fixtures = new_fixtures

        games = Games.query.filter(Games.tournament_id == tournament_id, Games.is_final == True).all()
        # idk something about glass houses?
        finals = defaultdict(list)
        for game in games:
            finals[game.round].append(game)
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
        tournament_id = get_tournament_id(tournament)
        games = Games.query.filter(Games.tournament_id == tournament_id, Games.is_final == False).all()

        # me when i criticize Jareds code then write this abomination
        fixtures = defaultdict(list)
        for game in games:
            fixtures[game.round].append(game)
        new_fixtures = {}
        for k, v in fixtures.items():
            new_fixtures[k] = [j for j in fixture_sorter(v)]
        fixtures = new_fixtures

        games = Games.query.filter(Games.tournament_id == tournament_id, Games.is_final == True).all()
        # idk something about glass houses?
        finals = defaultdict(list)
        for game in games:
            finals[game.round].append(game)
        return (
            render_template_sidebar(
                "tournament_specific/site_detailed.html",
                fixtures=fixtures.items(),
                finals=finals.items(),
                t=Tournaments.query.filter(Tournaments.searchable_name == tournament).first(),
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

        teams = db.session.query(Teams).join(TournamentTeams)
        if tournament:
            tournament_id = Tournaments.query.filter(Tournaments.searchable_name == tournament).first().id
            teams = teams.filter(TournamentTeams.tournament_id == tournament_id)
        teams = teams.group_by(Teams.id).order_by(Teams.searchable_name).all()
        return (
            render_template_sidebar(
                "tournament_specific/stats.html",
                teams=teams,
            ),
            200,
        )

    @app.get("/<tournament>/teams/<team_name>/")
    def team_site(tournament, team_name):
        tournament = Tournaments.query.filter(
            Tournaments.searchable_name == tournament).first().id if tournament else None
        team = Teams.query.filter(Teams.searchable_name == team_name).first()
        if not team:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This is not a real player",
                ),
                400,
            )
        players = team.players()
        game_filter = (lambda a: a.filter(Games.tournament_id == tournament, PlayerGameStats.team_id == team.id)) if tournament else lambda a: a.filter(PlayerGameStats.team_id == team.id)
        recent = db.session.query(Games, EloChange).join(PlayerGameStats,
                                                         PlayerGameStats.game_id == Games.id).outerjoin(EloChange,
                                                                                                        EloChange.game_id == Games.id).filter(
            Games.ended, PlayerGameStats.team_id == team.id, EloChange.player_id == PlayerGameStats.player_id)
        upcoming = db.session.query(Games).join(PlayerGameStats,
                                                PlayerGameStats.game_id == Games.id).filter(Games.ended == False,
                                                                                            Games.is_bye == False,
                                                                                            PlayerGameStats.team_id == team.id)
        if tournament:
            recent = recent.filter(Games.tournament_id == tournament)
            upcoming = upcoming.filter(Games.tournament_id == tournament)
        recent = recent.order_by(Games.id.desc()).limit(20).all()
        upcoming = upcoming.order_by(Games.id.desc()).limit(20).all()


        recent = [
            (
                f"{i.team_one.name} vs {i.team_two.name} [{i.team_one_score} - {i.team_two_score}] <{'' if e and e.elo_delta < 0 else '+'}{round(e.elo_delta, 2) if e else 0}>",
                i.id, i.tournament.searchable_name) for i, e in recent
        ]
        upcoming = [
            (
                f"{i.team_one.name} vs {i.team_two.name} [{i.team_one_score} - {i.team_two_score}]",
                i.id, i.tournament.searchable_name) for i in upcoming
        ]


        return (
            render_template_sidebar(
                "tournament_specific/each_team_stats.html",
                team=team,
                recent_games=recent,
                upcoming_games=upcoming,
                players=players,
                filter=game_filter
            ),
            200,
        )

    @app.get("/games/<true_game_id>/display")
    def scoreboard(true_game_id):
        if int(true_game_id) <= 0:
            game_id = Games.query.filter(Games.started, Games.court == abs(true_game_id)).order_by(
                Games.id.desc()).first().id
        else:
            game_id = int(true_game_id)

        game = Games.query.filter(Games.id == game_id).first()

        if not game:
            game_id = 113  # random placeholder game, this is the one where Tristan & zai beat me and alex 17 - 15
            game = Games.query.filter(Games.id == 113).first()

        pgs = PlayerGameStats.query.filter(PlayerGameStats.game_id == game_id).order_by(PlayerGameStats.team_id).all()

        players = [[i for i in pgs if i.team_id == pgs[0].team_id], [i for i in pgs if i.team_id != pgs[0].team_id]]

        teams = [i[0].team for i in players]  # bit cheeky but it works

        prev_event = GameEvents.query.filter(GameEvents.game_id == game_id).order_by(GameEvents.id.desc()).first()

        visual_swap = request.args.get("swap", "false") == "true"

        faulted = GameEvents.query.filter(GameEvents.game_id == game_id, (GameEvents.event_type == "Score") | (
                GameEvents.event_type == "Fault")).order_by(GameEvents.id.desc()).first()
        if faulted:
            faulted = faulted.event_type == "Fault"
        else:
            faulted = False

        team_card_times = [
            (max(i, key=lambda
                a: 9999999 if a.card_time_remaining < 0 else a.card_time_remaining).card_time_remaining,
             max(i, key=lambda a: 9999999 if a.card_time < 0 else a.card_time).card_time)
            for i in players]

        if visual_swap:
            teams = list(reversed(teams))
            players = list(reversed(players))

        sec = -int(game.length) if game.length and game.length > 0 else (game.start_time if game.started else -0)
        return (
            render_template_sidebar(
                "tournament_specific/scoreboard.html",
                game=game,
                players=players,
                faulted=faulted,
                teams=teams,
                team_card_times=team_card_times,
                visual_swap=visual_swap,
                prev_event=prev_event.event_type if prev_event else "a string that will not be matched with",
                time_elapsed=sec,
                update_count=manage_game.change_code(int(true_game_id)),
                timeout_time=manage_game.get_timeout_time(game_id) * 1000,
                serve_time=manage_game.get_serve_timer(game_id) * 1000,
                id=int(true_game_id)
            ),
            200,
        )

    @app.get("/games/display")
    def court_scoreboard():
        court = int(request.args.get("court"))
        return scoreboard(-court)

    @app.get("/games/<game_id>/")
    def game_site(game_id):
        game = Games.query.filter(Games.id == game_id).first()

        if not game:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="Game does not exist",
                ),
                404,
            )

        other_games = db.session.query(Games).filter(
            ((Games.team_one_id == game.team_one_id) & (Games.team_two_id == game.team_two_id))
            | ((Games.team_one_id == game.team_two_id) & (Games.team_two_id == game.team_one_id))
            , Games.tournament_id == game.tournament_id, Games.id != game.id).order_by(Games.id.desc()).limit(20).all()

        player_headers = [
            "Elo",
            "Points Scored",
            "Aces Scored",
            "Faults",
            "Double Faults",
            "Rounds on Court",
            "Rounds Carded",
            "Green Cards",
            "Yellow Cards",
            "Red Cards",
        ]

        pgs = PlayerGameStats.query.filter(PlayerGameStats.game_id == game_id).all()
        # quick and dirty hack
        players = [[i for i in pgs if i.team_id == pgs[0].team_id], [i for i in pgs if i.team_id != pgs[0].team_id]]
        teams = [players[0][0].team, players[1][0].team]  # quicker and dirtier hack
        team_stats: list[dict[str, float | str]] = []

        for i, t in enumerate(players):
            team_stats.append({
                "Elo": 0,
                "Faults": 0,
                "Double Faults": 0,
                "Green Cards": 0,
                "Yellow Cards": 0,
                "Red Cards": 0,
                "Timeouts Remaining": 0,
            })
            p: PlayerGameStats  # god i hate python typing
            for p in t:
                team_stats[i]["Elo"] += p.faults
                team_stats[i]["Green Cards"] += p.green_cards
                team_stats[i]["Yellow Cards"] += p.yellow_cards
                team_stats[i]["Red Cards"] += p.red_cards
                team_stats[i]["Faults"] += p.faults
                team_stats[i]["Double Faults"] += p.double_faults
                team_stats[i]["Elo"] += p.player.elo(last_game=game_id)
            team_stats[i]["Timeouts Remaining"] = 1 - (game.team_two_timeouts if i else game.team_one_timeouts)
            team_stats[i]["Elo"] = round(team_stats[i]["Elo"] / len(t), 2)
            elo_change = EloChange.query.filter(EloChange.player_id == t[0].player_id,
                                                EloChange.game_id == game_id).first()
            if elo_change:
                elo_delta = round(elo_change.elo_delta, 2)
                team_stats[i]["Elo"] = f'{team_stats[i]["Elo"]} [{"+" if elo_delta >= 0 else ""}{elo_delta}]'

        prev_matches = [
            (f"{i.team_one.name} vs {i.team_two.name} [{i.team_one_score} - {i.team_two_score}]", i.id,
             i.tournament.searchable_name) for i in other_games
        ]

        prev_matches = prev_matches or [("No other matches", -1, game.tournament.searchable_name)]
        return (
            render_template_sidebar(
                "tournament_specific/game_page.html",
                game=game,
                teams=teams,
                team_stats=team_stats,
                players=players,
                player_headings=player_headers,
                commentary=game_string_to_commentary(game.id),
                prev_matches=prev_matches,
                tournament=game.tournament.name,
                tournamentLink=game.tournament.searchable_name + "/",
            ),
            200,
        )

    @app.get("/<tournament>/ladder/")  # TODO: update to orm
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
            Team(i[2] if len(i[2]) < 20 else i[2][:18] + "...", i[1], i[4], i[3],
                 {k: v for k, v in zip(priority, i[5:])})
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

    @app.get("/<tournament_searchable>/players/")
    def players_site(tournament_searchable):
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
            "Rounds on Court": 5,
            "Points Served": 5,
            "Rounds Carded": 5,
            "Games Played": 5,
            "Games Won": 4,
        }
        player_headers = [
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
            "Rounds on Court",
            "Rounds Carded",
            "Points Served",
        ]

        players = People.query.all()
        tournament = Tournaments.query.filter(Tournaments.searchable_name == tournament_searchable).first()
        game_filter = (lambda a: a.filter(PlayerGameStats.tournament_id == tournament.id)) if tournament else None
        unranked = tournament is not None
        players_in = [(i, i.stats(games_filter=game_filter, include_unranked=unranked)) for i in players if
                      i.played_in_tournament(tournament_searchable)]
        players = []
        for i in players_in:
            players.append(
                (i[0].name, i[0].image(), i[0].searchable_name,
                 [(i[1][k], (priority_to_classname(priority[k]))) for k in player_headers]))
        return (
            render_template_sidebar(
                "tournament_specific/players.html",
                headers=[
                    (i - 1, k, priority_to_classname(priority[k]))
                    for i, k in enumerate(["Name"] + player_headers)
                ],
                players=sorted(players, key=lambda a: a[0]),
            ),
            200,
        )

    @app.get("/<tournament_searchable>/players/detailed")
    def detailed_players_site(tournament_searchable):
        players = People.query.all()
        tournament = Tournaments.query.filter(Tournaments.searchable_name == tournament_searchable).first()
        game_filter = (lambda a: a.filter(PlayerGameStats.tournament_id == tournament.id)) if tournament else None
        unranked = tournament is not None
        players = [(i, i.stats(games_filter=game_filter, include_unranked=unranked)) for i in players if
                   i.played_in_tournament(tournament_searchable)]
        return (
            render_template_sidebar(
                "tournament_specific/players_detailed.html",
                headers=[(i - 1, k) for i, k in enumerate(["Name"] + list(players[0][1].keys()))],
                players=players,
                tournament=link(tournament_searchable),
            ),
            200,
        )

    @app.get("/<tournament>/players/<player_name>/")
    def player_stats(tournament, player_name):
        tournament = Tournaments.query.filter(
            Tournaments.searchable_name == tournament).first().id if tournament else None
        player = People.query.filter(People.searchable_name == player_name).first()
        game_filter = (lambda a: a.filter(PlayerGameStats.tournament_id == tournament)) if tournament else lambda a: a
        stats = player.stats(games_filter=game_filter)
        team = db.session.query(Teams).join(TournamentTeams, TournamentTeams.team_id == Teams.id).filter(
            (Teams.captain_id == player.id) | (Teams.non_captain_id == player.id) | (
                    Teams.substitute_id == player.id))
        if tournament:
            team = team.filter(TournamentTeams.tournament_id == tournament)
        team = team.order_by(Teams.image_url.like("/api/teams/image%").desc(),
                             Teams.id).first()
        courts = [player.stats(games_filter=lambda a: game_filter(a).filter(Games.court == i)) for i in range(2)]
        recent = db.session.query(Games, EloChange).join(PlayerGameStats,
                                                         PlayerGameStats.game_id == Games.id).outerjoin(EloChange,
                                                                                                        EloChange.game_id == Games.id).filter(
            Games.ended, PlayerGameStats.player_id == player.id, EloChange.player_id == PlayerGameStats.player_id)
        upcoming = db.session.query(Games).join(PlayerGameStats,
                                                PlayerGameStats.game_id == Games.id).filter(Games.ended == False,
                                                                                            Games.is_bye == False,
                                                                                            PlayerGameStats.player_id == player.id)
        if tournament:
            recent = recent.filter(Games.tournament_id == tournament)
            upcoming = upcoming.filter(Games.tournament_id == tournament)
        recent = recent.order_by(Games.id.desc()).limit(20).all()
        upcoming = upcoming.order_by(Games.id.desc()).limit(20).all()

        if not player:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This is not a real player",
                ),
                400,
            )
        recent = [
            (
                f"{i.team_one.name} vs {i.team_two.name} [{i.team_one_score} - {i.team_two_score}] <{'' if e and e.elo_delta < 0 else '+'}{round(e.elo_delta, 2) if e else 0}>",
                i.id, i.tournament.searchable_name) for i, e in recent
        ]
        upcoming = [
            (
                f"{i.team_one.name} vs {i.team_two.name} [{i.team_one_score} - {i.team_two_score}]",
                i.id, i.tournament.searchable_name) for i in upcoming
        ]

        stats |= {
            f"Court {i + 1}": j for i, j in enumerate(courts)
        }

        if user_on_mobile():
            return (
                render_template_sidebar(
                    "tournament_specific/player_stats.html",
                    stats=stats,
                    name=player.name,
                    player=player_name,
                    team=team,
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
                    name=player.name,
                    player=player_name,
                    team=team,
                    recent_games=recent,
                    upcoming_games=upcoming,
                    insights=sorted(list(set(PlayerGameStats.rows.keys()) | set(Games.row_titles)))
                ),
                200,
            )

    @app.get("/<tournament>/officials/<nice_name>/")
    def official_site(tournament, nice_name):

        recent_games = []
        stats = {
            "Green Cards Given": 0,
            "Yellow Cards Given": 0,
            "Red Cards Given": 0,
            "Cards Given": 0,
            "Cards Per Game": 0,
            "Faults Called": 0,
            "Faults Per Game": 0,
            "Games Umpired": 0,
            "Games Scored": 0,
            "Rounds Umpired": 0
        }
        tournament_id = get_tournament_id(tournament)
        official = Officials.query.join(People).filter(People.searchable_name == nice_name).first()
        q = db.session.query(PlayerGameStats).join(Games, Games.id == PlayerGameStats.game_id).filter(
            Games.official_id == official.id)
        if tournament:
            q = q.filter(Games.tournament_id == tournament_id)
        prev_game_id = -1
        for pgs in q.all():
            stats["Green Cards Given"] += pgs.green_cards
            stats["Yellow Cards Given"] += pgs.yellow_cards
            stats["Red Cards Given"] += pgs.red_cards
            stats["Cards Given"] += pgs.green_cards + pgs.yellow_cards + pgs.red_cards
            stats["Faults Called"] += pgs.faults
            if pgs.game_id > prev_game_id:
                stats["Games Umpired"] += 1
                stats["Rounds Umpired"] += pgs.game.team_one_score + pgs.game.team_two_score

        q = Games.query.filter(Games.scorer_id == official.id)
        games = Games.query.filter((Games.official_id == official.id) | (Games.scorer_id == official.id))

        if tournament:
            q = q.filter(Games.tournament_id == tournament_id)
            games = games.filter(Games.tournament_id == tournament_id)
        games = games.all()
        stats["Games Scored"] = len(q.all())
        stats["Cards Per Game"] = round(stats["Cards Given"] / (stats["Games Umpired"] or 1), 2)
        stats["Faults Per Game"] = round(stats["Faults Called"] / (stats["Games Umpired"] or 1), 2)

        for g in games:
            recent_games.append(
                (
                    f"{'Umpire ' if g.official_id == official.id else 'Scorer'} Round {g.round + 1}: {g.team_one.name} - {g.team_two.name} ({g.team_one_score} - {g.team_two_score})",
                    g.id,
                    g.tournament.searchable_name,
                )
            )
        return (
            render_template_sidebar(
                "tournament_specific/official.html",
                name=official.person.name,
                link=nice_name,
                stats=[(k, v) for k, v in stats.items()],
                games=recent_games,
            ),
            200,
        )

    @app.get("/<tournament>/officials/")
    def official_directory_site(tournament):
        tournament_id = Tournaments.query.filter(Tournaments.searchable_name == tournament).first()
        official = TournamentOfficials.query
        if tournament_id:
            official = official.filter(TournamentOfficials.tournament_id == tournament_id.id)
        official = [i.official.person for i in official.all()]
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

        game = Games.query.filter(Games.id == game_id).first()

        if not game:
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="Game does not exist",
                ),
                404,
            )

        pgs = PlayerGameStats.query.filter(PlayerGameStats.game_id == game_id).all()
        # quick and dirty hack
        players = [[i for i in pgs if i.team_id == pgs[0].team_id], [i for i in pgs if i.team_id != pgs[0].team_id]]
        teams = [players[0][0].team, players[1][0].team]  # quicker and dirtier hack

        card_events = GameEvents.query.filter(
            (GameEvents.event_type == "Warning") | (GameEvents.event_type.like("% Card")),
            (GameEvents.team_id == game.team_one_id) | (GameEvents.team_id == game.team_two_id),
            GameEvents.tournament_id == game.tournament_id, GameEvents.game_id <= game.id).all()

        faulted = GameEvents.query.filter(GameEvents.game_id == game_id, (GameEvents.event_type == "Score") | (
                GameEvents.event_type == "Fault")).order_by(GameEvents.id.desc()).first()
        if faulted:
            faulted = faulted.event_type == "Fault"
        else:
            faulted = False

        @dataclass
        class Card:
            player: str
            team: int
            type: str
            reason: str
            hex: str

        cards = []

        COLORS = {
            "Warning": "#777777",
            "Green": "#84AA63",
            "Yellow": "C96500",
            "Red": "#EC4A4A"
        }

        for i in card_events:
            card_type = i.event_type.replace(" Card", "")
            c = Card(i.player.name, i.team_id, card_type, i.notes, COLORS[card_type])
            cards.append(c)

        game = Games.query.filter(Games.id == game_id).first()

        # teams = sorted(list(teams.values()), key=lambda a: a.sort)
        if visual_swap:
            teams = list(reversed(teams))
        team_one_players = sorted([((1 - i), v) for i, v in enumerate(players[0][:2])],
                                  key=lambda a: a[1].player.searchable_name)
        team_two_players = sorted([((1 - i), v) for i, v in enumerate(players[1][:2])],
                                  key=lambda a: a[1].player.searchable_name)
        all_officials = Officials.query.all()
        # TODO: Write a permissions decorator for scorers and primary officials
        # if key not in [game.primary_official.key, game.scorer.key] and not is_admin:
        #     return _no_permissions()

        if game.is_bye:
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
                    players=players,
                    teams=teams,
                    cards=cards,
                    all_officials=all_officials,
                    teamOneNames=[f"{i.player.searchable_name}:{i.player.name}" for i in players[0]],
                    teamTwoNames=[f"{i.player.searchable_name}:{i.player.name}" for i in players[1]],
                    game=game,
                    swap=visual_str,
                    admin=True,  # key in [i.key for i in get_all_officials() if i.admin]
                ),
                200,
            )
        else:
            team_card_times = [
                (max(i, key=lambda
                    a: 9999999 if a.card_time_remaining < 0 else a.card_time_remaining).card_time_remaining,
                 max(i, key=lambda a: 9999999 if a.card_time < 0 else a.card_time).card_time)
                for i in players]
            return (
                render_template(
                    f"tournament_specific/game_editor/edit_game.html",
                    players=players,
                    teamOnePlayers=team_one_players,
                    teamTwoPlayers=team_two_players,
                    cards=cards,
                    teamOneNames=[f"{i.player.searchable_name}:{i.player.name}" for i in players[0]],
                    teamTwoNames=[f"{i.player.searchable_name}:{i.player.name}" for i in players[1]],
                    swap=visual_str,
                    teams=teams,
                    enum_teams=enumerate(teams),
                    game=game,
                    team_card_times=team_card_times,
                    timeout_time=manage_game.get_timeout_time(game_id) * 1000,
                    timeout_first=manage_game.get_timeout_caller(game_id),
                    match_points=0 if (
                                max(game.team_one_score, game.team_two_score) < 10 or game.someone_has_won) else abs(
                        game.team_one_score - game.team_two_score),
                    VERBAL_WARNINGS=Config().use_warnings,
                    GREEN_CARDS=Config().use_green_cards,
                    faulted=faulted
                ),
                200,
            )

    @officials_only
    @app.get("/games/<game_id>/finalise")
    def finalise_game(game_id):
        visual_swap = request.args.get("swap", "false") == "true"
        visual_str = "true" if visual_swap else "false"

        game = Games.query.filter(Games.id == game_id).first()

        player_headers = [
            "Elo",
            "Points Scored",
            "Aces Scored",
            "Faults",
            "Double Faults",
            "Rounds on Court",
            "Rounds Carded",
            "Green Cards",
            "Yellow Cards",
            "Red Cards",
        ]

        pgs = PlayerGameStats.query.filter(PlayerGameStats.game_id == game_id).all()
        # quick and dirty hack
        players = [[i for i in pgs if i.team_id == pgs[0].team_id], [i for i in pgs if i.team_id != pgs[0].team_id]]
        teams = [players[0][0].team, players[1][0].team]  # quicker and dirtier hack

        if game.someone_has_won:
            return (
                render_template(
                    "tournament_specific/game_editor/team_signatures.html",
                    swap=visual_str,
                    teams=teams,
                    players=players,
                    game=game,
                    headers=player_headers
                ),
                200,
            )

    @app.get("/<tournament_name>/create")
    @officials_only
    def create_game(tournament_name):
        tournament = Tournaments.query.filter(Tournaments.searchable_name == tournament_name).first()
        teams = Teams.query.order_by(Teams.searchable_name).all()
        officials = Officials.query.join(People).order_by(People.searchable_name).all()
        print(officials)

        if not get_type_from_name(tournament.fixtures_type, tournament.id).manual_allowed():
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This competition cannot be edited manually!",
                ),
                400,
            )

        key = fetch_user()
        official = [i for i in officials if i.person.password == key]
        officials = official + [i for i in officials if i.person.password != key]

        return (
            render_template(
                "tournament_specific/game_editor/create_game_teams.html",
                tournamentLink=link(tournament.searchable_name),
                officials=officials,
                teams=teams,
            ),
            200,
        )

    @officials_only
    @app.get("/<tournament_name>/create_players")
    def create_game_players(tournament_name):
        tournament = Tournaments.query.filter(Tournaments.searchable_name == tournament_name).first()
        players = People.query.order_by(People.searchable_name).all()
        officials = Officials.query.join(People).order_by(People.searchable_name).all()
        if not get_type_from_name(tournament.fixtures_type, tournament.id).manual_allowed():
            return (
                render_template(
                    "tournament_specific/game_editor/game_done.html",
                    error="This competition cannot be edited manually!",
                ),
                400,
            )

        key = fetch_user()

        official = [i for i in officials if i.person.password == key]
        officials = official + [i for i in officials if i.person.password != key]
        return (
            render_template(
                "tournament_specific/game_editor/create_game_players.html",
                tournamentLink=link(tournament_name),
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
