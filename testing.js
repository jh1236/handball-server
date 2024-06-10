const sleep = ms => new Promise(r => setTimeout(r, ms));

function start(id) {
    return fetch("http://localhost/api/games/update/start", {
        method: "POST",
        body: JSON.stringify({
            id: id,
            swapService: false,
            teamOneIGA: true
        }),
        headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    })
}

function score(id, firstTeam, leftPlayer) {
    return fetch("http://localhost/api/games/update/score", {
        method: "POST", body: JSON.stringify({
            id: id,
            firstTeam: firstTeam,
            leftPlayer: leftPlayer
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    })
}


function forfeit(id, firstTeam) {
    return fetch("http://localhost/api/games/update/forfeit", {
        method: "POST", body: JSON.stringify({
            id: id,
            firstTeam: firstTeam,
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    })
}


function finish(id) {
    return fetch("http://localhost/api/games/update/end", {
        method: "POST",
        body: JSON.stringify({
            id: id,
            notes: '',
            protestTeamOne: false,
            protestTeamTwo: false
        }),
        headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    })
}

all_games = [[398, 399, 400], [401, 403, 404], [405, 406, 408], [409, 410, 411], [413, 414, 415], [420, 418, 417], [424, 423, 421], [425, 426], [427, 428]]

async function a() {
    for (const j of all_games) {
        console.log(j)
        for (const i of j) {
            start(i).then(
                (res) => {
                    if (res.status === 204) {
                        score(i, false, true).then(
                            (res) => {
                                if (res.status === 204) {
                                    forfeit(i, true).then(
                                        (res) => {
                                            if (res.status === 204) {
                                                finish(i).then(
                                                    (res) => {
                                                        if (res.status === 204) {
                                                            console.log("game ended")
                                                        } else {
                                                            throw new DOMException("didnt work")
                                                        }
                                                    }
                                                );
                                            } else {
                                                throw new DOMException("didnt work")
                                            }
                                        }
                                    );
                                } else {
                                    throw new DOMException("didnt work")
                                }
                            }
                        );
                    } else {
                        throw new DOMException("didnt work")
                    }
                }
            );

        }
        await sleep(8000)
    }
}

a()