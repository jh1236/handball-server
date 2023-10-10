let id = 0
let tournament = "";
let setId = newId => id = newId
let setTournament = t => tournament = t
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

let lookup = ["One", "Two"]

let teamListOne = ["", ""]
let teamListTwo = ["", ""]
let setTeamListOne = (d, s, i) => {
    teamListOne[i] = d
    document.getElementById("teamOne" + i).textContent = `Player ${lookup[i]}: ${s}`
}

let setTeamListTwo = (d, s, i) => {
    teamListTwo[i] = d
    document.getElementById("teamTwo" + i).textContent = `Player ${lookup[i]}: ${s}`
}
let left = false
let right = false
let first_serves = true

setLeft = (i, s) => {
    left = i
    document.getElementById("left").textContent = "Left Player: " + s
}
setRight = (i, s) => {
    right = i
    document.getElementById("right").textContent = "Left Player: " + s
}
setTeamServing = (i, s) => {
    right = i
    document.getElementById("team").textContent = "Team Serving: " + s
}

function start() {
    fetch("/api/games/update/start", {
        method: "POST",
        body: JSON.stringify({
            id: id,
            firstTeamServed: first_serves,
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
    }).then(() => document.location.href = `/${tournament}games/` + id + "/"
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
    }).then(() => document.location.href = `/${tournament}games/` + id + "/"
    );
}

function finish() {
    fetch("/api/games/update/end", {
        method: "POST",
        body: JSON.stringify({
            id: id,
            tournament: tournament.replace("/", ""),
            bestPlayer: best
        }),
        headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => document.location.href = `/${tournament}games/` + id + "/");
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