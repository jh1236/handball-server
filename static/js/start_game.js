let id = 0
let tournament = "";
let teamsSwapped = false

let lxor = (a, b) => a ? !b : b

let setup = (newId, newSwapped) => {
    id = newId
    teamsSwapped = newSwapped
}

function swap() {
    if (document.location.href.includes("swap")) {
        document.location.href = window.location.href.replace("?swap=true", "")
    } else {
        document.location.href = window.location.href + "?swap=true"
    }
}

let setTournament = t => {
    tournament = t
}
let best = ""
setBest = (i, s) => {
    best = i
    document.getElementById("rename").textContent = "Fairest And Best: " + s
}

let teamOne = ""
let setTeamOne = (i, s) => {
    teamOne = i
    document.getElementById("teamOne").textContent = "Team One: " + s
}

let teamTwo = ""
let setTeamTwo = (i, s) => {
    teamTwo = i
    document.getElementById("teamTwo").textContent = "Team Two: " + s
}

let official = ""
let setOfficial = (i, s) => {
    official = i
    document.getElementById("umpire").textContent = "Official: " + s
}
let scorer = ""
let setScorer = (i, s) => {
    scorer = i
    document.getElementById("scorer").textContent = "Scorer: " + s
}

let lookup = ["Player One", "Player Two", "Substitute"]

let teamListOne = ["", ""]
let teamListTwo = ["", ""]
let setTeamListOne = (d, s, i) => {
    teamListOne[i] = d
    document.getElementById("teamOne" + i).textContent = `${lookup[i]}: ${s}`
}

let setTeamListTwo = (d, s, i) => {
    teamListTwo[i] = d
    document.getElementById("teamTwo" + i).textContent = `${lookup[i]}: ${s}`
}
let left = false
let right = false
let first_serves = !teamsSwapped

setLeft = (i, s) => {
    if (teamsSwapped) {
        right = i
    } else {
        left = i
    }
    document.getElementById("left").textContent = "Left Player: " + s
}
setRight = (i, s) => {
    if (teamsSwapped) {
        left = i
    } else {
        right = i
    }
    document.getElementById("right").textContent = "Left Player: " + s
}
setTeamServing = (i, s) => {
    first_serves = i
    document.getElementById("team").textContent = "Team Serving: " + s
}

function start() {
    if (official) {
        fetch("/api/games/update/start", {
            method: "POST",
            body: JSON.stringify({
                id: id,
                firstTeamServed: lxor(first_serves, teamsSwapped),
                swapTeamOne: left,
                swapTeamTwo: right,
                official: official,
                scorer: scorer,
                tournament: tournament.replace("/", "")
            }),
            headers: {
                "Content-type": "application/json; charset=UTF-8"
            }
        }).then(() => location.reload());
        return
    }
    fetch("/api/games/update/start", {
        method: "POST",
        body: JSON.stringify({
            id: id,
            firstTeamServed: lxor(first_serves, teamsSwapped),
            swapTeamOne: left,
            swapTeamTwo: right,
            tournament: tournament.replace("/", "")
        }),
        headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => location.reload());
}

function createPlayers() {
    fetch("/api/games/update/create", {
        method: "POST",
        body: JSON.stringify({
            teamOne: document.getElementById("nameOne").value,
            teamTwo: document.getElementById("nameTwo").value,
            playersOne: teamListOne,
            playersTwo: teamListTwo,
            official: official,
            tournament: tournament.replace("/", "")
        }),
        headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(
        (res) => {
            if (res.ok) {
                res.json().then(
                    o => {
                        document.location.href = `/${tournament}games/` + o.id + "/edit"
                    }
                )
            } else {
                alert("Error!")
            }
        }
    );
}

function createTeams() {
    fetch("/api/games/update/create", {
        method: "POST",
        body: JSON.stringify({
            teamOne: teamOne,
            teamTwo: teamTwo,
            official: official,
            tournament: tournament.replace("/", "")
        }),
        headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(
        (res) => {
            if (res.ok) {
                res.json().then(
                    o => {
                        document.location.href = `/${tournament}games/` + o.id + "/edit"
                    }
                )
            } else {
                alert("Error!")
            }
        }
    );
}

function finish(cards_len) {
    let cards = []
    for (let i = 1; i <= cards_len; i++) {
        cards.push(document.getElementById(`card${i}`).value)
    }
    fetch("/api/games/update/end", {
        method: "POST",
        body: JSON.stringify({
            id: id,
            tournament: tournament.replace("/", ""),
            bestPlayer: best,
            notes: document.getElementById("notes").value,
            cards: cards
        }),
        headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(
        (res) => {
            if (res.status === 204) {
                document.location.href = `/${tournament}games/` + id
            } else {
                alert("Error!")
            }
        }
    );
}


function protest() {
    fetch("/api/games/update/protest", {
        method: "POST",
        body: JSON.stringify({
            id: id,
            tournament: tournament.replace("/", ""),
            teamOne: document.getElementById("protest0").checked,
            teamTwo: document.getElementById("protest1").checked,
        }),
        headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => location.reload());
}


function undo() {
    fetch("/api/games/update/undo", {
        method: "POST", body: JSON.stringify({
            tournament: tournament.replace("/", ""),
            id: id
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => location.reload());
}

function del() {
    fetch("/api/games/update/undo", {
        method: "POST", body: JSON.stringify({
            tournament: tournament.replace("/", ""),
            id: id
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => document.location.href = `/${tournament}`);
}

function myFunction(button) {
    button.parentElement.getElementsByClassName("dropdown-content")[0].classList.toggle("show")
}

// Close the dropdown menu if the user clicks outside of it
window.onclick = function (event) {
    if (!event.target.matches('.dropbtn')) {
        const dropdowns = document.getElementsByClassName("dropdown-content");
        let i;
        for (i = 0; i < dropdowns.length; i++) {
            const openDropdown = dropdowns[i];
            if (openDropdown.classList.contains('show')) {
                openDropdown.classList.remove('show');
            }
        }
    }
}