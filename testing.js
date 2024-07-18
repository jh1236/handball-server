const sleep = ms => new Promise(r => setTimeout(r, ms));

const readline = require('node:readline');

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
});


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

let startCount = 397
let end = 420

async function a() {
    let test = ''
    while (test !== 'x') {
        for (let i = startCount; i < end; i++) {
            console.log(i)
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
                        console.log(`${i} didnt work`)
                    }
                }
            );

        }
        rl.question(`What's your name?`, name => {
            test = name
            rl.close();
        });
    }
}

a()