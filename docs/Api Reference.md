# API REFERENCE

## Game editing Endpoints

### GET /api/games/change_code

#### Description

Returns the id of the most recent GameEvent for a game. Used to know if a game has an update

#### Permisions:

The user must be logged in as an official to use this endpoint

#### Arguments:

- id: int
    - The id of the game

#### Return Structure

- code: int = The id of the most recent update to the game

<hr>

### POST /api/games/update/start

#### Description

Starts a game in the system, setting the side of the court and the team who is serving first.

#### Permisions:

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

### POST /api/games/update/score

#### Description

Adds one to the score of a team.

#### Permisions:

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

### POST /api/games/update/ace

#### Permisions:

Adds one to the score of a team, and adds an ace statistic to the relevant player

#### Arguments:

- id: int
    - The id of the game

#### Return Structure

- N/A

<hr>

### POST /api/games/update/substitute

#### Description

Used to swap a substitute onto the court.

#### Permisions:

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

### POST /api/games/update/pardon

#### Description

Allows a player to return to the court early from being carded

#### Permisions:

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

### POST /api/games/update/end

#### Description

Ends a game, setting a fairest & best and taking notes and protests.

#### Permisions:

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

### POST /api/games/update/timeout

#### Description

Starts a timeout for a given team

#### Permisions:

The user must be logged in as an official to use this endpoint

#### Arguments:

- id: int
    - The id of the game
- firstTeam: bool
    - True if the team listed first called the timeout

#### Return Structure

- N/A

<hr>

### POST /api/games/update/forfeit

#### Description

Forfeits the game for a team, setting their opponent's score
to either 11 or 2 plus their score, whichever is greater.

#### Permisions:

The user must be logged in as an official to use this endpoint

#### Arguments:

- id: int
    - The id of the game
- firstTeam: bool
    - True if the team listed first is forfeiting

#### Return Structure

- N/A

<hr>

### POST /api/games/update/timeout

#### Description

Starts a timeout for a given team

#### Permisions:

The user must be logged in as an official to use this endpoint

#### Arguments:

- id: int
    - The id of the game
- firstTeam: bool
    - True if the team listed first called the timeout

#### Return Structure

- N/A

<hr>

### POST /api/games/update/endTimeout

#### Description

Ends the current timeout for a game

#### Permisions:

The user must be logged in as an official to use this endpoint

#### Arguments:

- id: int
    - The id of the game

#### Return Structure

- N/A

<hr>

### POST /api/games/update/serveClock

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

### POST /api/games/update/fault

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

### POST /api/games/update/official_timeout

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


### POST /api/games/update/undo

#### Description

Undoes the last game event, unless the previous event was an end timeout, in which case it undoes the last 2 events.

#### Permissions:

The user must be logged in as an official to use this endpoint

#### Arguments:

- id: int
    - The id of the game


#### Return Structure

- N/A

<hr>
