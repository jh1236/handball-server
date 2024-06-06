let id = 0
let tournament = "";
let teamsSwapped = false


let setTournament = t => {
    tournament = t
}
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



let firstServes = true
let firstIga = true

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

let teamOnePlayers = document.currentScript.getAttribute('teamOne').split(",")
let teamTwoPlayers = document.currentScript.getAttribute('teamTwo').split(",")

let playerLookup = {}
for (let i of teamOnePlayers.concat(teamTwoPlayers)) {
    playerLookup[i.split(":")[0]] = i.split(":")[1]
}
teamOnePlayers = teamOnePlayers.map(i => i.split(":")[0])
teamTwoPlayers = teamTwoPlayers.map(i => i.split(":")[0])
function setTeamOneLeftPlayer(i) {
    if (teamsSwapped) {
        for (const j in teamTwoPlayers) {
            console.log(`${j} === ${i}`)
            if (teamTwoPlayers[j] === i) {
                [teamTwoPlayers[0], teamTwoPlayers[j]] = [teamTwoPlayers[j], teamTwoPlayers[0]]
                break
            }
        }
        document.getElementById("teamOneLeft").textContent = "Left Player: " + playerLookup[teamTwoPlayers[0]]
        if (teamTwoPlayers.length > 2) {
            document.getElementById("teamOneRight").textContent = "Right Player: " + playerLookup[teamTwoPlayers[1]]
        }
    } else {
        for (const j in teamOnePlayers) {
            console.log(`${j} === ${i}`)
            if (teamOnePlayers[j] === i) {
                [teamOnePlayers[0], teamOnePlayers[j]] = [teamOnePlayers[j], teamOnePlayers[0]]
                break
            }
        }
        document.getElementById("teamOneLeft").textContent = "Left Player: " + playerLookup[teamOnePlayers[0]]
        if (teamOnePlayers.length > 2) {
            document.getElementById("teamOneRight").textContent = "Right Player: " + playerLookup[teamOnePlayers[1]]
        }
    }
    console.log(teamOnePlayers)
    console.log(teamTwoPlayers)
}

function setTeamTwoLeftPlayer(i, s) {
    if (teamsSwapped) {
        for (const j in teamOnePlayers) {
            if (teamOnePlayers[j] === i) {
                [teamOnePlayers[0], teamOnePlayers[j]] = [teamOnePlayers[j], teamOnePlayers[0]]
                break
            }
        }
        document.getElementById("teamTwoLeft").textContent = "Left Player: " + playerLookup[teamOnePlayers[0]]
        if (teamOnePlayers.length > 2) {
            document.getElementById("teamTwoRight").textContent = "Right Player: " + playerLookup[teamOnePlayers[1]]
        }
    } else {
        for (const j in teamTwoPlayers) {
            if (teamTwoPlayers[j] === i) {
                [teamTwoPlayers[0], teamTwoPlayers[j]] = [teamTwoPlayers[j], teamTwoPlayers[0]]
                break
            }
        }
        document.getElementById("teamTwoLeft").textContent = "Left Player: " + playerLookup[teamTwoPlayers[0]]
        if (teamTwoPlayers.length > 2) {
            document.getElementById("teamTwoRight").textContent = "Right Player: " + playerLookup[teamTwoPlayers[1]]
        }
    }
    console.log(teamOnePlayers)
    console.log(teamTwoPlayers)
}

function setTeamOneRightPlayer(i, s) {
    if (teamsSwapped) {
        for (const j in teamTwoPlayers) {
            if (teamTwoPlayers[j] === i) {
                [teamTwoPlayers[1], teamTwoPlayers[j]] = [teamTwoPlayers[j], teamTwoPlayers[1]]
                break
            }
        }
        document.getElementById("teamOneLeft").textContent = "Left Player: " + playerLookup[teamTwoPlayers[0]]
        if (teamTwoPlayers.length > 2) {
            document.getElementById("teamOneRight").textContent = "Right Player: " + playerLookup[teamTwoPlayers[1]]
        }
    } else {
        for (const j in teamOnePlayers) {
            if (teamOnePlayers[j] === i) {
                [teamOnePlayers[1], teamOnePlayers[j]] = [teamOnePlayers[j], teamOnePlayers[1]]
                break
            }
        }
        document.getElementById("teamOneLeft").textContent = "Left Player: " + playerLookup[teamOnePlayers[0]]
        if (teamOnePlayers.length > 2) {
            document.getElementById("teamOneRight").textContent = "Right Player: " + playerLookup[teamOnePlayers[1]]
        }
    }
    console.log(teamOnePlayers)
    console.log(teamTwoPlayers)

}

function setTeamTwoRightPlayer(i, s) {
    if (teamsSwapped) {
        for (const j in teamOnePlayers) {
            if (teamOnePlayers[j] === i) {
                [teamOnePlayers[1], teamOnePlayers[j]] = [teamOnePlayers[j], teamOnePlayers[1]]
                break
            }
        }
        document.getElementById("teamTwoLeft").textContent = "Left Player: " + playerLookup[teamOnePlayers[0]]
        if (teamOnePlayers.length > 2) {
            document.getElementById("teamTwoRight").textContent = "Right Player: " + playerLookup[teamOnePlayers[1]]
        }
    } else {
        for (const j in teamTwoPlayers) {
            if (teamTwoPlayers[j] === i) {
                [teamTwoPlayers[1], teamTwoPlayers[j]] = [teamTwoPlayers[j], teamTwoPlayers[1]]
                break
            }
        }
        document.getElementById("teamTwoLeft").textContent = "Left Player: " + playerLookup[teamTwoPlayers[0]]
        if (teamTwoPlayers.length > 2) {
            document.getElementById("teamTwoRight").textContent = "Right Player: " + playerLookup[teamTwoPlayers[1]]
        }
    }
    console.log(teamOnePlayers)
    console.log(teamTwoPlayers)
}

function setTeamServing(i, s) {
    firstServes = i
    document.getElementById("team").textContent = "Team Serving: " + s
}

function setTeamIGA(i, s) {
    firstIga = i
    document.getElementById("iga").textContent = "IGA Side: " + s
}

function start() {
    if (official || scorer) {
        fetch("/api/games/update/start", {
            method: "POST",
            body: JSON.stringify({
                id: id,
                swapService: !lxor(firstServes, teamsSwapped),
                teamOneIGA: firstIga,
                teamOne: teamOnePlayers,
                teamTwo: teamTwoPlayers,
                official: official,
                scorer: scorer,
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
            swapService: !lxor(firstServes, teamsSwapped),
            teamOneIGA: firstIga,
            teamOne: teamOnePlayers,
            teamTwo: teamTwoPlayers,
        }),
        headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => location.reload());
}

function undo() {
    fetch("/api/games/update/undo", {
        method: "POST", body: JSON.stringify({
            id: id
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => location.reload());
}

function del() {
    fetch("/api/games/update/undo", {
        method: "POST", body: JSON.stringify({
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