import datetime
import time
from collections import defaultdict
from dataclasses import dataclass

from flask import render_template

from FixtureGenerators.FixturesGenerator import get_type_from_name
from database import db
from database.models import Games, Tournaments, EloChange, PlayerGameStats, GameEvents
from structure.GameUtils import game_string_to_events
from structure.get_information import get_tournament_id
from utils.databaseManager import DatabaseManager
from utils.permissions import admin_only
from utils.sidebar_wrapper import render_template_sidebar
from utils.util import fixture_sorter
from website.tournament_specific import priority_to_classname
from website.website import numbers


def add_admin_pages(app):
    @app.get("/<tournament>/fixtures/admin")
    @admin_only
    def admin_fixtures(tournament):
        tournament_id = get_tournament_id(tournament)
        games = Games.query.filter(Games.tournament_id == tournament_id, Games.is_final == False).all()

        # me when i criticize Jareds code then write this abomination
        fixtures = defaultdict(list)
        for game in games:
            fixtures[game.round].append(game)
            print(game.official)
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
                "tournament_specific/admin/site.html",
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


    @app.get("/games/<game_id>/admin")
    @admin_only
    def admin_game_site(game_id):
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
            "Yellow": "#C96500",
            "Red": "#EC4A4A"
        }

        card_events = GameEvents.query.filter(
            (GameEvents.event_type == "Warning") | (GameEvents.event_type.like("% Card")),
            (GameEvents.team_id == game.team_one_id) | (GameEvents.team_id == game.team_two_id), GameEvents.game_id == game.id).all()


        for i in card_events:
            card_type = i.event_type.replace(" Card", "")
            c = Card(i.player.name, i.team_id, card_type, i.notes, COLORS[card_type])
            cards.append(c)

        prev_matches = prev_matches or [("No other matches", -1, game.tournament.searchable_name)]
        return (
            render_template_sidebar(
                "tournament_specific/admin/game_page.html",
                game=game,
                teams=teams,
                team_stats=team_stats,
                player_headings=player_headers,
                players=players,
                commentary=game_string_to_events(game.id),
                cards=cards,
                prev_matches=prev_matches,
                tournament=game.tournament.name,
                tournamentLink=game.tournament.searchable_name + "/",
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
                                         INNER JOIN people captain_id ON captain_id.id = inside.captain_id
                                         LEFT JOIN people non_captain_id ON non_captain_id.id = inside.non_captain_id
                                         LEFT JOIN people sub ON sub.id = inside.substitute_id
                                where eloChange.player_id = sub.id
                                   or eloChange.player_id = captain_id.id
                                   or eloChange.player_id = non_captain_id.id AND eloChange.id <=
                                      (SELECT MAX(id) FROM eloChange WHERE eloChange.tournament_id = tournaments.id)), 0)
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
       ROUND(1500.0 + (SELECT SUM(elo_delta)
                       from eloChange
                       where eloChange.player_id = people.id AND eloChange.id <=
                                      (SELECT MAX(id) FROM eloChange WHERE eloChange.tournament_id = playerGameStats.tournament_id)), 2) as elo,
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
            cards = c.execute(
                """SELECT type, reason, hex, game_id, people.name
FROM punishments INNER JOIN teams ON teams.id = team_id INNER JOIN people ON player_id = people.id
WHERE teams.searchable_name = ?
  AND tournament_id = ?""", (team_name, tournament_id)).fetchall()
            key_games = c.execute(
                """ SELECT s.name, r.name, g1.team_one_score, g1.team_two_score, g1.id, tournaments.searchable_name, noteable_status
                    FROM games g1
                             INNER JOIN tournaments on g1.tournament_id = tournaments.id
                             INNER JOIN teams r on g1.team_two_id = r.id
                             INNER JOIN teams s on g1.team_one_id = s.id
                    WHERE (r.searchable_name = ? or s.searchable_name = ?) and tournaments.searchable_name = ? and g1.ended = 1 AND g1.noteable_status <> 'Official'
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
                "tournament_specific/admin/stats.html",
                teams=teams,
            ),
            200,
        )

    # TODO: complete
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
                """SELECT teams.image_url,
       people.searchable_name,
       people.name,
       coalesce(SUM(games.best_player_id = player_id), 0),
       ROUND(1500.0 + coalesce((SELECT SUM(elo_delta)
                       from eloChange
                       where eloChange.player_id = people.id AND eloChange.id <=
                                      (SELECT MAX(id) FROM eloChange WHERE eloChange.tournament_id = tournaments.id)), 0), 2) as elo,
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
       teams.searchable_name,
       coalesce(SUM(games.best_player_id = player_id), 0),
       ROUND(1500.0 + (SELECT SUM(elo_delta)
                       from eloChange
                       where eloChange.player_id = people.id AND eloChange.id <=
                                      (SELECT MAX(id) FROM eloChange WHERE eloChange.tournament_id = playerGameStats.tournament_id)), 2) as elo,
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
       ROUND(coalesce(CAST(100.0 * SUM(games.best_player_id = player_id) AS REAL) / COUNT(DISTINCT playerGameStats.game_id),
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

  and IIF(? is NULL, 1, tournamentTeams.tournament_id = ?)""",
                (tournament_id, player_name, tournament_id, tournament_id), ).fetchone()

            courts = c.execute(
                """SELECT people.name,
       people.searchable_name,
       coalesce(SUM(games.best_player_id = player_id), 0),
       ROUND(1500.0 + (SELECT SUM(elo_delta)
                       from eloChange
                       where eloChange.player_id = people.id AND eloChange.id <=
                                      (SELECT MAX(id) FROM eloChange WHERE eloChange.tournament_id = playerGameStats.tournament_id)), 2) as elo,
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
       ROUND(coalesce(CAST(100.0 * SUM(playerGameStats.points_scored) AS REAL) / (SELECT SUM(i.points_scored)
                                                                           from playerGameStats i
                                                                           where i.team_id = teams.id
                                                                             and i.tournament_id = tournamentTeams.tournament_id),
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
         LEFT JOIN games on (teams.id = games.team_one_id OR teams.id = team_two_id)
          AND games.tournament_id = tournamentTeams.tournament_id and games.is_bye = 0
                                and games.is_final = 0
                                and (iif(? is null, games.ranked, 1) or teams.non_captain_id is null)
         LEFT JOIN playerGameStats on people.id = playerGameStats.player_id AND games.id = playerGameStats.game_id
WHERE people.searchable_name = ?
  and IIF(? is NULL, 1, tournamentTeams.tournament_id = ?) AND court >= 0
  group by games.court""",
                (tournament_id, player_name, tournament_id, tournament_id)).fetchall()

            cards = c.execute(
                """SELECT type, reason, hex, game_id, people.name
FROM punishments INNER JOIN people ON player_id = people.id
WHERE people.searchable_name = ?
  AND tournament_id = ?""", (player_name, tournament_id)).fetchall()
            key_games = c.execute(
                """ SELECT s.name, r.name, g1.team_one_score, g1.team_two_score, g1.id, tournaments.searchable_name, noteable_status
                    FROM games g1
                             INNER JOIN tournaments on g1.tournament_id = tournaments.id
                             INNER JOIN teams r on g1.team_two_id = r.id
                             INNER JOIN teams s on g1.team_one_id = s.id
                             INNER JOIN playerGameStats on g1.id = playerGameStats.game_id
                             INNER JOIN people on playerGameStats.player_id = people.id
                    WHERE people.searchable_name = ? and IIF(? is NULL, 1, tournaments.id = ?) and g1.is_bye = 0 AND g1.noteable_status <> 'Official'
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
                cards=cards,
                key_games=key_games

            ),
            200,
        )

    @app.get("/<tournament>/admin")
    @admin_only
    def admin_home_page(tournament):
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
            requires_action_string: str = ""

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
                                 name, teams.searchable_name, SUM(games.winning_team_id = teams.id) as gamesWon, COUNT(games.id) as gamesPlayed, pool 
                                 FROM tournamentTeams 
                                 INNER JOIN teams ON tournamentTeams.team_id = teams.id
                                 INNER JOIN games ON (teams.id = games.team_one_id OR teams.id = games.team_two_id) AND tournamentTeams.tournament_id = games.tournament_id 
                                 WHERE games.tournament_id = ? AND NOT games.is_final AND NOT games.is_bye
                                 group by teams.id 
                                 ORDER BY 
                                     CAST(gamesWon AS REAL) / gamesPlayed DESC  
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
                                serving.name, receiving.name, team_one_score, team_two_score, games.id, games.admin_status 
                                FROM games 
                                INNER JOIN teams AS serving ON games.team_one_id = serving.id 
                                INNER JOIN teams as receiving ON games.team_two_id = receiving.id 
                                WHERE 
                                    tournament_id = ? AND NOT games.is_bye AND (admin_status <> 'Resolved' AND admin_status <> 'Official' AND admin_status <> 'Forfeited');
                            """,
                (tournament_id,),
            ).fetchall()
            games_requiring_action = [
                Game(game[:2], f"{game[2]} - {game[3]}", game[4], game[5]) for game in games
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
                                    people.name, searchable_name, sum(yellow_cards) * 5 + sum(red_cards) * 10, sum(warnings), sum(yellow_cards), sum(red_cards), sum(rounds_carded) 
                                    FROM playerGameStats 
                                    INNER JOIN people ON player_id = people.id 
                                    WHERE 
                                        tournament_id = ?
                                    GROUP BY player_id 
                                    ORDER BY 
                                        sum(yellow_cards) * 5 + sum(red_cards) * 10 DESC 
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
