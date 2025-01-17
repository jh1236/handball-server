# PLAYERS API REFERENCE

## GET endpoints

### /api/players

#### Description

Returns all players, adjusted for a tournament if passed in.

#### Permissions:

This endpoint is open to the public.

#### Arguments:

- tournament: str (Optional)
    - The searchable name of the tournament to get officials from
- team: str (Optional)
    - The searchable name of the team that the players play on
- includeStats: bool (Optional)
    - True if the stats of each player should be included

#### Return Structure

- list\[Person\]

<hr>

### /api/players/<searchable>

#### Description

Returns the details of a single player, with the option to filter stats from a certain tournament
or game.  If the game is passed, a PlayerGameStats is returned, otherwise a Player is returned

#### Permissions:

This endpoint is open to the public.

#### Arguments:

- searchable: str
    - The searchable name of the player to get stats for
- tournament: str (Optional)
    - The searchable name of the tournament to get stats from
- game: str (Optional)
    - The searchable name of the tournament to get stats from

#### Return Structure

- Person | PlayerGameStats   (See description)

<hr>

### /api/users/image

#### Description

Returns the image for a given user.

#### Permissions:

This endpoint is open to the public.

#### Arguments:

- name: str (Optional)
  - The searchable name of the user to get an image from

#### Return Structure

- image

<hr>