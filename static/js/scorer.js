let id = 0
let tournament = ""
let teamsSwapped = false
let teamName = ""
let startTime = -1

const CARDS = {
    Warning: {
        "swearing": "Audible Swearing",
        "dissent": "Disrespect Towards Officials",
        "timeWasting": "Delay of Game",
        "spokeOutOfTurn": "Spoke to Umpire from Outside BRA",
        "allowedNonCaptain": "Allowed Non Captain to Speak To Umpire",
    },
    Yellow: {
        "directedSwearing": "Swearing Towards Players or Officials",
        "badDissent": "Continuous or Egregious Disrespect Towards Officials",
        "badTimeWasting": "Deliberate Delay of Game",
        "equipmentAbuse": "Equipment Abuse",
        "danger": "Dangerous Play (James)",
        "misconduct": "Misconduct Whilst Carded",
        "aggression": "Displays of Aggression towards Officials or Players"
    },
    Red: {
        "violence": "Violence Towards Any Player, Official Or Spectator",
        "veryBadDissent": "Disruptive or Unrelenting Disrespect Towards Officials",
        "badEquipmentAbuse": "Equipment Abuse in a Deliberately Violent Manner",
        "cheatingAccusation": "Accusations Of Cheating",
        "discrimination": "Any Form of Discrimination"
    },
}

CARDS.Green = CARDS.Warning

let setup = (newId, newSwapped) => {
    id = newId
    teamsSwapped = newSwapped
}
setTournament = t => tournament = t

function swap() {
    if (document.location.href.includes("swap")) {
        document.location.href = window.location.href.replace("?swap=true", "")
    } else {
        document.location.href = window.location.href + "?swap=true"
    }
}

let teamOnePlayers = document.currentScript.getAttribute('teamOne').split(",")
let teamTwoPlayers = document.currentScript.getAttribute('teamTwo').split(",")

let playerLookup = {}
for (let i of teamOnePlayers.concat(teamTwoPlayers)) {
    playerLookup[i.split(":")[0]] = i.split(":")[1]
}
teamOnePlayers = teamOnePlayers.map(i => i.split(":")[0])
teamTwoPlayers = teamTwoPlayers.map(i => i.split(":")[0])

let lxor = (a, b) => a ? !b : b

let timeoutTime = -1

function score(firstTeam, leftPlayer) {
    fetch("/api/games/update/score", {
        method: "POST", body: JSON.stringify({
            id: id,
            firstTeam: lxor(Boolean(firstTeam), teamsSwapped),
            leftPlayer: leftPlayer
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(
        (res) => {
            if (res.ok) {
                location.reload()
            } else {
                alert("Error!")
            }
        }
    );
}

function sub(firstTeam, firstPlayer) {
    fetch("/api/games/update/substitute", {
        method: "POST", body: JSON.stringify({
            id: id,
            firstTeam: lxor(Boolean(firstTeam), teamsSwapped),
            tournament: tournament.replace("/", ""),
            firstPlayer: firstPlayer,
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(
        (res) => {
            if (res.ok) {
                location.reload()
            } else {
                alert("Error!")
            }
        }
    );
}

function ace() {
    fetch("/api/games/update/ace", {
        method: "POST", body: JSON.stringify({
            id: id,
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(
        (res) => {
            if (res.ok) {
                location.reload()
            } else {
                alert("Error!")
            }
        }
    );
}


let first = null
let color = null

function openCardModal(colorIn, firstTeam, teamName) {
    first = firstTeam
    color = colorIn
    players = firstTeam ? teamOnePlayers : teamTwoPlayers
    document.getElementById("myModal").style.display = "block";
    document.getElementById("cardHeader").textContent = `${colorIn} Card for ${teamName}`;
    firstTeamSelected = firstTeam
    console.log(players)
    document.getElementById("nameOne").textContent = playerLookup[players[0]]
    document.getElementById("nameTwo").textContent = playerLookup[players[1]]
    if (colorIn === "Yellow") {
        document.getElementById("duration").style.display = "block"
        document.getElementById("durationText").style.display = "block"
        document.getElementById("duration").value = "3"
        document.getElementById("durationText").textContent = "Duration (3)"
    } else {
        document.getElementById("duration").style.display = "none"
        document.getElementById("durationText").style.display = "none"
    }
    const reasons = document.getElementById("reason")
    reasons.replaceChildren()
    for (const k in CARDS[colorIn]) {
        const v = CARDS[colorIn][k]
        reasons.insertAdjacentHTML( 'beforeend',`<input type="radio" name="reason" id="${k}" value="${k}"><label for="${k}">${v}</label><br>`)
    }
    if (colorIn !== "Green" && colorIn !== "Warning") {
        reasons.insertAdjacentHTML( 'beforeend',`<input type="radio" name="reason" id="repeated" value="repeated"><label for="repeat">Repeated :`)
        let sel = "<select id='repeatedSelect'>"
        for (const k in CARDS.Warning) {
            const v = CARDS.Warning[k]
            sel += `<option id="${k}" name="${k}">${v}</option>`
        }
        if (colorIn === "Red") {
            for (const k in CARDS.Yellow) {
                const v = CARDS.Yellow[k]
                sel += `<option id="${k}" name="${k}">${v}</option>`
            }
        }
        sel += "</select></label><br>"
        reasons.insertAdjacentHTML( 'beforeend',sel)
    }
    reasons.insertAdjacentHTML( 'beforeend',`<input type="radio" name="reason" id="other" value="other"><input type="text" id="otherText"><br>`)
}

function sendCustomCard() {
    let selectedReason = document.querySelector('input[name="reason"]:checked')
    const selectedPlayer = document.getElementById('playerOne').checked
    if (!selectedReason) {
        alert("Please Select A Reason!")
        return
    }
    selectedReason = selectedReason.value
    if (!selectedPlayer && !document.getElementById('playerTwo').checked) {
        alert("Please Select A Player!")
        return
    }
    let reason
    console.log(selectedReason)
    if (selectedReason === "other") {
        reason = document.getElementById("otherText").value
    } else if (selectedReason === "repeated") {
        reason = "Repeated " + document.getElementById("repeatedSelect").value
    } else {
        reason = CARDS[color][selectedReason]
    }
    if (!reason) {
        alert("Please Select A Reason!")
        return
    }

    fetch("/api/games/update/card", {
        method: "POST", body: JSON.stringify({
            id: id,
            firstTeam: lxor(first, teamsSwapped),
            leftPlayer: selectedPlayer,
            color: color,
            duration: +(document.getElementById("duration").value) % 10,
            reason: reason
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(
        (res) => {
            if (res.ok) {
                location.reload()
            } else {
                alert("Error!")
            }
        }
    );
}

function next() {
    document.location = `/games/${id}/finalise`
}


function timeoutOverlayOld(timeIn = Date.now() + 30000) {
    document.getElementById("myNav").style.width = "100%";
    timeoutTime = timeIn
    window.onscroll = function () {
        window.scrollTo(0, 100);
    };

    function named(x) {
        if (timeoutTime < 0 || (timeoutTime - Date.now() < 0)) {
            window.onscroll = function () {
            };
            endTimeout()
            document.getElementById("myNav").style.width = "0%";
            return
        } else {
            document.getElementById("timeoutClock").style = ""
            setTimeout(named, 100)
        }
        document.getElementById("timeoutClock").textContent = "" + Math.round((timeoutTime - Date.now()) / 100) / 10
    }

    named()
}

function timeoutOverlay(timeIn = 0, firstTeam) {
    if (timeIn > 0) {
        timeoutTime = timeIn
    }
    let clock = Math.round((timeoutTime - Date.now()) / 100) / 10
    let element;
    if (firstTeam) {
        element = document.getElementById("timeoutOne")
    } else {
        element = document.getElementById("timeoutTwo")
    }
    if (timeoutTime < 0) return
    teamName = element.textContent.split("Timeout ")[1].split(":")[0]
    element.style = "font-size:18px;font-weight:bold"
    element.textContent = `Timeout ${teamName}: ${clock.toFixed(1)}`
    setTimeout(() => {
        timeoutOverlay(-1, firstTeam)
    }, 10)
}


function startServeClock() {
    if (startTime > 0) {
        stopServeClock()
        return
    }
    serveClock(Date.now() + 8000)
    fetch("/api/games/update/serve_clock", {
        method: "POST", body: JSON.stringify({
            id: id,
            start: true,
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    });
}

function forfeit(firstTeam) {
    fetch("/api/games/update/forfeit", {
        method: "POST", body: JSON.stringify({
            id: id,
            firstTeam: lxor(Boolean(firstTeam), teamsSwapped),
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => document.location.reload());
}

function stopServeClock() {
    startTime = -1
    document.getElementById("serveBtn").style = ""
    document.getElementById("serveBtn").textContent = "Start Serve Timer"
    fetch("/api/games/update/serve_clock", {
        method: "POST", body: JSON.stringify({
            id: id,
            start: false,
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    });
}

function serveClock(timeIn = 0) {
    if (timeIn > 0) {
        startTime = timeIn
    }
    let clock = Math.round((startTime - Date.now()) / 100) / 10
    document.getElementById("serveBtn").textContent = `Serve Timer: ${clock.toFixed(1)}`
    document.getElementById("serveBtn").style = "font-size:18px;font-weight:bold"
    if (clock > -3) {
        setTimeout(serveClock, 10)
    } else {
        startTime = -1
        document.getElementById("serveBtn").style = ""
        document.getElementById("serveBtn").textContent = "Start Serve Timer"
    }
}

function timeout(firstTeam) {
    if (timeoutTime > 0) {
        endTimeout(firstTeam)
        return
    }
    timeoutOverlay(Date.now() + 30000, firstTeam)
    fetch("/api/games/update/timeout", {
        method: "POST", body: JSON.stringify({
            id: id,
            firstTeam: lxor(Boolean(firstTeam), teamsSwapped),
            tournament: tournament.replace("/", ""),
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    });
}

function endTimeout(firstTeam) {
    timeoutTime = -1
    if (firstTeam) {
        element = document.getElementById("timeoutOne")
    } else {
        element = document.getElementById("timeoutTwo")
    }
    element.style = ""
    element.innerHTML = `<s>Timeout ${teamName}</s>`
    fetch("/api/games/update/endTimeout", {
        method: "POST", body: JSON.stringify({
            id: id,
            tournament: tournament.replace("/", ""),
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => document.location.reload());
}


function fault() {
    fetch("/api/games/update/fault", {
        method: "POST", body: JSON.stringify({
            id: id,
        }), headers: {
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

function swapServe() {
    fetch("/api/games/update/swapServe", {
        method: "POST", body: JSON.stringify({
            tournament: tournament.replace("/", ""),
            id: id
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => location.reload());
}

function swapServeTeam() {
    fetch("/api/games/update/swapServeTeam", {
        method: "POST", body: JSON.stringify({
            tournament: tournament.replace("/", ""),
            id: id
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => location.reload());
}

function swapPlayerSides(first) {
    fetch("/api/games/update/swapPlayerSides", {
        method: "POST", body: JSON.stringify({
            tournament: tournament.replace("/", ""),
            id: id,
            firstTeam: first
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
    if (event.target.matches('.modal')) {
        document.getElementById("myModal").style.display = "none";
    }
}
window.onload = () => {
    document.getElementsByClassName("close")[0].onclick = function () {
        document.getElementById("myModal").style.display = "none";
    };
    document.getElementById("duration").addEventListener("input", (event) => {
        document.getElementById("durationText").textContent = `Duration (${event.target.value})`;
    });
}