# API REFERENCE

## GET endpoints

### /api/games/change_code

#### Description

Returns the id of the most recent GameEvent for a game. Used to know if a game has an update

#### Permissions:

The user must be logged in as an official to use this endpoint

#### Arguments:

- id: int
    - The id of the game

#### Return Structure

- code: int = The id of the most recent update to the game

<hr>

### /api/games/<id>

#### Description

Returns the data for a single game 

#### Permissions:

This endpoint is open to the public

#### Arguments:

- id: int
    - The id of the game
- includeGameEvents: bool
    - True if the events of the game should be included
- includePlayerStats
    - True if the stats of each player should be included
  
#### Return Structure

- Game(includeGameEvents=includeGameEvents)

<hr>

### /api/games

#### Description

Returns the list of games matching the given criteria

#### Permissions:

This endpoint is open to the public

#### Arguments:

- tournament: str (Optional)
    - The searchable name of the tournament to take games from
- team: str (Optional) (Repeatable)
    - The searchable name of the team who played in the game
- player: str (Optional) (Repeatable)
    - The searchable name of the player who played in the game
- official: str (Optional) (Repeatable)
    - The searchable name of the official who umpired or scored the game
- court
    - The court the game was played on
- includeGameEvents (bool) (Optional) (**admin** only)
    - True if the events of the games should be included
- includePlayerStats (bool) (Optional)(**admin** only)
    - True if the stats of each player should be included

#### Return Structure

- list\[Game(includeGameEvents=includeGameEvents)\]

<hr>

### /api/fixtures

#### Description

Returns the fixtures for a given tournament

#### Permissions:

This endpoint is open to the public

#### Arguments:

- tournament: str (Optional)
    - The searchable name of the tournament to take games from
- team: str (Optional) (Repeatable)
    - The searchable name of the team who played in the game
- player: str (Optional) (Repeatable)
    - The searchable name of the player who played in the game
- official: str (Optional) (Repeatable)
    - The searchable name of the official who umpired or scored the game
- court
    - The court the game was played on
- includeGameEvents
    - True if the events of the games should be included
- includePlayerStats
    - True if the stats of each player should be included

#### Return Structure

- list\[Game(includeGameEvents=includeGameEvents)\]

<hr>
<hr>

## POST endpoints

### /api/games/update/start

#### Description

Starts a game in the system, setting the side of the court and the team who is serving first.

#### Permissions:

The user must be logged in as an official to use this endpoint

#### Arguments:

- id: int
    - The id of the game
- swapService: bool
    - True if the team listed first is not serving
- teamOneIGA: bool
    - True if the team listed first is on the IGA side of the court
- teamOne: list\[str\]
    - The searchable names of each player on team one, in the order \[Left Player, Right Player, Substitute\]
- teamTwo: list\[str\]
    - The searchable names of each player on team two, in the order \[Left Player, Right Player, Substitute\]
- official: str (Optional)
    - the searchable name of the person who is officiating the game
- scorer: str (Optional)
    - the searchable name of the person who is scoring the game

#### Return Structure

- N/A

<hr>

### /api/games/update/score

#### Description

Adds one to the score of a team.

#### Permissions:

The user must be logged in as an official to use this endpoint

#### Arguments:

- id: int
    - The id of the game
- firstTeam: bool
    - True if the team listed first scored the point
- leftPlayer: bool
    - True if the player who started the point on the left side scored the point

#### Return Structure

<hr>

- N/A

### /api/games/update/ace

#### Permissions:

Adds one to the score of a team, and adds an ace statistic to the relevant player

#### Arguments:

- id: int
    - The id of the game

#### Return Structure

- N/A

<hr>

### /api/games/update/substitute

#### Description

Used to swap a substitute onto the court.

#### Permissions:

The user must be logged in as an official to use this endpoint

#### Arguments:

- id: int
    - The id of the game
- firstTeam: bool
    - True if the team listed first is substituting
- leftPlayer: bool
    - True if the player who is currently on the left side is going to substitute

#### Return Structure

- N/A

<hr>

### /api/games/update/pardon

#### Description

Allows a player to return to the court early from being carded

#### Permissions:

The user must be logged in as an **admin** to use this endpoint

#### Arguments:

- id: int
    - The id of the game
- firstTeam: bool
    - True if the team listed first is substituting
- leftPlayer: bool
    - True if the player who is currently on the left side is going to substitute

#### Return Structure

- N/A

<hr>

### /api/games/update/resolve

#### Description

Marks the game as resolved, clearing the notification that it needs to be processed

#### Permissions:

The user must be logged in as an **admin** to use this endpoint

#### Arguments:

- id: int
    - The id of the game

#### Return Structure

- N/A

<hr>

### /api/games/update/end

#### Description

Ends a game, setting a fairest & best and taking notes and protests.

#### Permissions:

The user must be logged in as an official to use this endpoint

#### Arguments:

- id: int
    - The id of the game
- bestPlayer: str
    - The searchable name of the player who played best
- notes: str
    - Any notes that the umpire would like to leave for the tournament director
- protestTeamOne: str (Optional)
    - If present, represents the reason that team one wants to protest
- protestTeamTwo: str (Optional)
    - If present, represents the reason that team two wants to protest

#### Return Structure

- N/A

<hr>

### /api/games/update/timeout

#### Description

Starts a timeout for a given team

#### Permissions:

The user must be logged in as an official to use this endpoint

#### Arguments:

- id: int
    - The id of the game
- firstTeam: bool
    - True if the team listed first called the timeout

#### Return Structure

- N/A

<hr>

### /api/games/update/forfeit

#### Description

Forfeits the game for a team, setting their opponent's score
to either 11 or 2 plus their score, whichever is greater.

#### Permissions:

The user must be logged in as an official to use this endpoint

#### Arguments:

- id: int
    - The id of the game
- firstTeam: bool
    - True if the team listed first is forfeiting

#### Return Structure

- N/A

<hr>

### /api/games/update/timeout

#### Description

Starts a timeout for a given team

#### Permissions:

The user must be logged in as an official to use this endpoint

#### Arguments:

- id: int
    - The id of the game
- firstTeam: bool
    - True if the team listed first called the timeout

#### Return Structure

- N/A

<hr>

### /api/games/update/endTimeout

#### Description

Ends the current timeout for a game

#### Permissions:

The user must be logged in as an official to use this endpoint

#### Arguments:

- id: int
    - The id of the game

#### Return Structure

- N/A

<hr>

### /api/games/update/serveClock

#### Description

Either starts or ends the serve clock.

#### Permissions:

The user must be logged in as an official to use this endpoint

#### Arguments:

- id: int
    - The id of the game
- start: bool
    - True if the clock is being started, False if the clock is being ended

#### Return Structure

- N/A

<hr>

### /api/games/update/fault

#### Description

Adds a fault to the current server, if this is their second fault, gives a point to the other team.

#### Permissions:

The user must be logged in as an official to use this endpoint

#### Arguments:

- id: int
    - The id of the game

#### Return Structure

- N/A

<hr>

### /api/games/update/official_timeout

#### Description

Starts an official timeout.

#### Permissions:

The user must be logged in as an official to use this endpoint

#### Arguments:

- id: int
    - The id of the game

#### Return Structure

- N/A

<hr>

### /api/games/update/undo

#### Description

Undoes the last game event, unless the previous event was an end timeout, in which case it undoes the last 2 events.

#### Permissions:

The user must be logged in as an official to use this endpoint.
If the game has ended, the user must be logged in as an **admin** to use this endpoint.

#### Arguments:

- id: int
    - The id of the game

#### Return Structure

- N/A

<hr>

### /api/games/update/delete

#### Description

Deletes a game.

#### Permissions:

The user must be logged in as an official to use this endpoint.
If the game has started, the user must be logged in as an **admin** to use this endpoint.

#### Arguments:

- id: int
    - The id of the game

#### Return Structure

- N/A

<hr>

### /api/games/update/card

#### Description

Cards a player in a game.

#### Permissions:

The user must be logged in as an official to use this endpoint.

#### Arguments:

- id: int
    - The id of the game
- firstTeam: bool
    - True if the team listed first is receiving the card
- leftPlayer: bool
    - True if the player who is currently on the left side is receiving the card
- color: "Warning" | "Green" | "Yellow" | "Red"
    - the type of card that the player has been issued
- duration: int
    - the amount of rounds the player is off for (-1 for the rest of the game)
- reason: str
    - the reason that the card was given

#### Return Structure

- N/A

<hr>

### /api/games/update/create

#### Description

Creates a new game.

#### Permissions:

The user must be logged in as an official to use this endpoint.

#### Arguments:

- tournament: str
    - The searchable name of the tournament for the new game
- teamOne: str
    - The searchable name of team one, or the new name for team one if it is new
- teamTwo: str
    - The searchable name of team two, or the new name for team one if it is new
- official: str
    - the searchable name of the umpire for the gane
- scorer: str (Optional)
    - the searchable name of the scorer for the gane
- playersOne: list\[str\] (Optional)
    - a list of the **true names** of the players in team one. Any new players will be implicitly created
- playersTwo: list\[str\] (Optional)
    - a list of the **true names** of the players in team two. Any new players will be implicitly created

#### Return Structure

- N/A

<hr>
