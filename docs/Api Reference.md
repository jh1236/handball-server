# API REFERENCE

## Game editing Endpoints

### GET /api/games/change_code

#### Description

Returns the id of the most recent GameEvent for a game. Used to know if a game has an update

#### Permisions:

The user must be logged in as an official to use this endpoint

#### Arguments:

- id: int
    - The id of the game to get the change code for

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
    - The id of the game to start
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
    - The id of the game that the score is for
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
    - The id of the game that the ace is for
- firstTeam: bool
    - True if the team listed first scored the point

#### Return Structure

- N/A

<hr>

### POST /api/games/update/substitute

#### Description

Indicates

#### Permisions:

The user must be logged in as an official to use this endpoint

#### Arguments:

- id: int
    - The id of the game that the substitute is for
- firstTeam: bool
    - True if the team listed first is substituting
- leftPlayer: bool
    - True if the player who is currently on the left side is going to substitute

#### Return Structure

- N/A

<hr>

### POST /api/games/update/pardon

#### Permisions:

The user must be logged in as an **admin** to use this endpoint

#### Arguments:

- id: int
    - The id of the game that the substitute is for
- firstTeam: bool
    - True if the team listed first is substituting
- leftPlayer: bool
    - True if the player who is currently on the left side is going to substitute

#### Return Structure

- N/A

<hr>
