# API REFERENCE

## GET endpoints

### /api/officials

#### Description

Returns all officials and their stats, adjusted for a tournament if passed in

#### Permissions:

This endpoint is open to the public.

#### Arguments:

- tournament: str (Optional)
    - The searchable name of the tournament to get officials from

#### Return Structure

- Official

<hr>

### /api/officials/<searchable>

#### Description

Returns the details of a single official, with the option to filter stats from a certain tournament

#### Permissions:

This endpoint is open to the public.

#### Arguments:

- tournament: str (Optional)
    - The searchable name of the tournament to get stats from

#### Return Structure

- Official

<hr>
