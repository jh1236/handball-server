# API REFERENCE

## GET endpoints

### /api/login

#### Description

Logs in a user

#### Permissions:

This endpoint is open to the public.

#### Arguments:

- userId: int
    - the ID of the user attempting to log in
- password: str
    - the password of the user attempting to log in

#### Return Structure

- token: str
    - the token that the user received

<hr>
<hr>

## POST endpoints

### /api/image/

#### Description

Changes the users image to be the image at a given URL.

#### Permissions:

The user must be logged in as an official to use this endpoint.

#### Arguments:

- imageLocation: url
    - The URL of an image.

#### Return Structure

- N/A

<hr>
