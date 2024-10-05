let id = 0
let tournament = ""
let teamsSwapped = false
let teamName = ""
let startTime = -1
let lastScoreTime = -1

let waiting = false
let greenCardsUsed = document.currentScript.getAttribute('greens') === 'True'
let warningsUsed = document.currentScript.getAttribute('warnings') === 'True'

let CARDS = {}

if (greenCardsUsed && warningsUsed) {
    CARDS = {
        Warning: {
            "swearing": "Audible Swearing",
            "timeWasting": "Delay of Game",
            "endOfGameProcess": "Did not follow the end of game process"
        },
        Green: {
            "dissent": "Disrespect Towards Officials",
            "danger": "Dangerous Play (James)",
            "badTimeWasting": "Deliberate Delay of Game",
            "hindrance" : "Deliberately Hindering another Player",
            "uniform" : "Not Meeting the Uniform Requirements"
        },
        Yellow: {
            "badDissent": "Continuous or Egregious Disrespect Towards Officials",
            "equipmentAbuse": "Equipment Abuse",
            "danger": "Aggressively Dangerous Play (James)",
            "misconduct": "Misconduct Whilst Carded",
            "aggression": "Displays of Aggression towards Officials or Players",
            "bypass": "Attempting to Get Around the restrictions on swearing"
        },
        Red: {
            "violence": "Violence Towards Any Player, Official Or Spectator",
            "veryBadDissent": "Disruptive or Unrelenting Disrespect Towards Officials",
            "badEquipmentAbuse": "Equipment Abuse in a Deliberately Violent Manner",
            "cheatingAccusation": "Accusations Of Cheating",
            "discrimination": "Any Form of Discrimination"
        }
    }
} else if (greenCardsUsed) {
    CARDS = {
        Green: {
            "swearing": "Audible Swearing",
            "dissent": "Disrespect Towards Officials",
            "timeWasting": "Delay of Game",
            "spokeOutOfTurn": "Spoke to Umpire from Outside BRA",
            "allowedNonCaptain": "Allowed Non Captain to Speak to Umpire",
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
        }
    }
} else if (warningsUsed) {
    CARDS = {
        Warning: {
            "swearing": "Audible Swearing",
            "dissent": "Disrespect Towards Officials",
            "timeWasting": "Delay of Game",
            "spokeOutOfTurn": "Spoke to Umpire from Outside BRA",
            "allowedNonCaptain": "Allowed Non Captain to Speak to Umpire",
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
} else {
    CARDS = {
        Yellow: {
            "swearing": "Audible Swearing",
            "dissent": "Disrespect Towards Officials",
            "timeWasting": "Delay of Game",
            "spokeOutOfTurn": "Spoke to Umpire from Outside BRA",
            "allowedNonCaptain": "Allowed Non Captain to Speak to Umpire",
            "directedSwearing": "Swearing Towards Players or Officials",
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
}
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
    if (waiting) return
    waiting = true
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
            waiting = false
            if (res.ok) {
                location.reload()
            } else {
                alert("Error!")
            }
        }
    );
}

function pardon(firstTeam, leftPlayer) {
    if (waiting) return
    waiting = true
    fetch("/api/games/update/pardon", {
        method: "POST", body: JSON.stringify({
            id: id,
            firstTeam: lxor(Boolean(firstTeam), teamsSwapped),
            leftPlayer: leftPlayer
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(
        (res) => {
            waiting = false
            if (res.ok) {
                location.reload()
            } else {
                alert("Error!")
            }
        }
    );
}

function sub(firstTeam, firstPlayer) {
    if (waiting) return
    waiting = true
    fetch("/api/games/update/substitute", {
        method: "POST", body: JSON.stringify({
            id: id,
            firstTeam: lxor(Boolean(firstTeam), teamsSwapped),
            leftPlayer: firstPlayer,
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(
        (res) => {
            waiting = false
            if (res.ok) {
                location.reload()
            } else {
                alert("Error!")
            }
        }
    );
}

function ace() {
    if (waiting) return
    waiting = true
    fetch("/api/games/update/ace", {
        method: "POST", body: JSON.stringify({
            id: id,
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(
        (res) => {
            waiting = false
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
    console.log(players.length)
    document.getElementById("nameOne").textContent = playerLookup[players[0]].replace(/[\n\r]/g, '')
    if (players.length > 1) {
        document.getElementById("nameTwo").textContent = playerLookup[players[1]].replace(/[\n\r]/g, '')
        document.getElementById("nameTwo").style.display = ""
        document.getElementById("playerTwo").style.display = ""
    } else {
        document.getElementById("nameTwo").style.display = "none"
        document.getElementById("playerTwo").style.display = "none"
    }


    if (colorIn === "Yellow") {
        document.getElementById("duration").style.display = "block"
        minYellowTime = 3 * warningsUsed + 3 * greenCardsUsed
        document.getElementById("duration").value = `${minYellowTime}`
        document.getElementById("duration").min = `${minYellowTime}`
        document.getElementById("duration").value = `${minYellowTime}`
        document.getElementById("durationText").style.display = "block"
        document.getElementById("durationText").textContent = `Duration (${minYellowTime})`
    } else {
        document.getElementById("duration").style.display = "none"
        document.getElementById("durationText").style.display = "none"
    }
    const reasons = document.getElementById("reason")
    reasons.replaceChildren()
    for (const k in CARDS[colorIn]) {
        const v = CARDS[colorIn][k]
        reasons.insertAdjacentHTML('beforeend', `<input type="radio" name="reason" id="${k}" value="${k}"><label for="${k}">${v}</label><br>`)
    }
    if (colorIn === "Red" || (colorIn === "Yellow" && (warningsUsed || greenCardsUsed)) || (colorIn === "Green" && warningsUsed)) {
        reasons.insertAdjacentHTML('beforeend', `<input type="radio" name="reason" id="repeated" value="repeated"><label for="repeat">Repeated :`)
        let sel = "<select id='repeatedSelect'>"
        if (warningsUsed) {
            for (const k in CARDS.Warning) {
                const v = CARDS.Warning[k]
                sel += `<option id="${k}" name="${k}">${v}</option>`
            }
        }
        if (colorIn !== "Green" && greenCardsUsed) {
            for (const k in CARDS.Green) {
                const v = CARDS.Green[k]
                sel += `<option id="${k}" name="${k}">${v}</option>`
            }
        } else if (colorIn === "Red") {
            for (const k in CARDS.Yellow) {
                const v = CARDS.Yellow[k]
                sel += `<option id="${k}" name="${k}">${v}</option>`
            }
        }
        sel += "</select></label><br>"
        reasons.insertAdjacentHTML('beforeend', sel)
    }
    reasons.insertAdjacentHTML('beforeend', `<input type="radio" name="reason" id="other" value="other"><input type="text" id="otherText"><br>`)
}

function sendCustomCard() {
    if (waiting) return
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
    waiting = true
    let duration;
    if (color === 'Red') {
        duration = -1
    } else if (color === 'Yellow') {
        duration = document.getElementById("duration").value
    } else if (color === 'Green' && warningsUsed) {
        duration = 2
    } else {
        duration = 0
    }

    fetch("/api/games/update/card", {
        method: "POST", body: JSON.stringify({
            id: id,
            firstTeam: lxor(first, teamsSwapped),
            leftPlayer: selectedPlayer,
            color: color,
            duration: duration,
            reason: reason
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(
        (res) => {
            waiting = false
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
    if (firstTeam === 1) {
        element = document.getElementById("timeoutOne")
    } else if (firstTeam === 0) {
        element = document.getElementById("timeoutTwo")
    } else {
        console.log(timeoutTime)
        clock = Math.round((Date.now() - timeoutTime) / 100) / 10
        element = document.getElementById("timeoutOfficial")
    }
    if (timeoutTime < 0) return
    teamName = element.textContent.split(":")[0]
    element.style = "font-size:18px;font-weight:bold"
    element.textContent = ` ${teamName}: ${clock.toFixed(1)}`
    setTimeout(() => {
        timeoutOverlay(-1, firstTeam)
    }, 10)
}

function umpireTimeout() {
    if (waiting) return
    waiting = true
    if (timeoutTime > 0) {
        endTimeout(null)
        return
    }
    timeoutOverlay(Date.now(), null)
    fetch("/api/games/update/official_timeout", {
        method: "POST", body: JSON.stringify({
            id: id,
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(
        (res) => {
            waiting = false
            if (!res.ok) {
                alert("Error!")
            }
        }
    );
}

function lastScoreTimer(timeIn = 0) {
    console.log(lastScoreTime)
    if (timeIn > 0) {
        lastScoreTime = timeIn
    }


    let clock = Math.round((lastScoreTime - Date.now()) / 100) / 10
    let element = document.getElementById("readyTimer")
    let timeLeft = (lastScoreTime - Date.now()) / 1000
    element.textContent = `Ready Timer: ${clock.toFixed(1)}` // what the fuck do you mean "toFixed???
    if (timeLeft > 10) {
        element.style = "font-size: 30px;font-weight:bold;display:inline"
    } else if (timeLeft > 5) {
        element.textContent = `Ready Timer: ${clock.toFixed(1)}` // what the fuck do you mean "toFixed???
        if (Math.floor(timeLeft) % 2 === 0) {
            element.style = "font-size: 30px;display:inline"
        } else {
            element.style = "font-size: 30px;font-weight:bold;display:inline"
        }
    } else if (timeLeft > 0) {
        element.style = "font-size: 30px;font-weight:bold;display:inline; color: red;"
    }
    if (timeLeft < -5){
        element.style = "font-size: 30px;display:none"
        element.textContent = 'Serve Timer'
    } else {
        setTimeout(() => {lastScoreTimer(-1)}, 10)
    }
}


function startServeClock() {
    if (waiting) return
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
    if (waiting) return
    waiting = true
    fetch("/api/games/update/forfeit", {
        method: "POST", body: JSON.stringify({
            id: id,
            firstTeam: lxor(Boolean(firstTeam), teamsSwapped),
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(
        (res) => {
            waiting = false
            if (res.ok) {
                location.reload()
            } else {
                alert("Error!")
            }
        }
    );
}

function stopServeClock() {
    if (waiting) return
    waiting = true
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
    }).then(
        (res) => {
            waiting = false
            if (res.ok) {
                location.reload()
            } else {
                alert("Error!")
            }
        }
    );
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
    if (waiting) return
    waiting = true
    if (timeoutTime > 0) {
        endTimeout(firstTeam)
        return
    }
    timeoutOverlay(Date.now() + 30000, Number(firstTeam))
    fetch("/api/games/update/timeout", {
        method: "POST", body: JSON.stringify({
            id: id,
            firstTeam: lxor(Boolean(firstTeam), teamsSwapped),
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(
        (res) => {
            waiting = false
            if (!res.ok) {
                alert("Error!")
            }
        }
    );
}

function endTimeout(firstTeam) {
    timeoutTime = -1
    if (firstTeam) {
        element = document.getElementById("timeoutOne")
    } else if (firstTeam != null) {
        element = document.getElementById("timeoutTwo")
    } else {
        element = document.getElementById("timeoutOfficial")
    }
    element.style = ""
    if (firstTeam != null) {
        element.innerHTML = `<s>${teamName}</s>`
    } else {
        element.innerHTML = teamName
    }
    fetch("/api/games/update/end_timeout", {
        method: "POST", body: JSON.stringify({
            id: id,
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(
        (res) => {
            waiting = false
            if (res.ok) {
                location.reload()
            } else {
                alert("Error!")
            }
        }
    );
}


function fault() {
    if (waiting) return
    waiting = true
    fetch("/api/games/update/fault", {
        method: "POST", body: JSON.stringify({
            id: id,
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(
        (res) => {
            waiting = false
            if (res.ok) {
                location.reload()
            } else {
                alert("Error!")
            }
        }
    );
}


function undo() {
    if (waiting) return
    waiting = true
    fetch("/api/games/update/undo", {
        method: "POST", body: JSON.stringify({
            id: id
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(
        (res) => {
            waiting = false
            if (res.ok) {
                location.reload()
            } else {
                alert("Error!")
            }
        }
    );
}

function swapServe() {
    if (waiting) return
    waiting = true
    fetch("/api/games/update/swapServe", {
        method: "POST", body: JSON.stringify({
            id: id
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(
        (res) => {
            waiting = false
            if (res.ok) {
                location.reload()
            } else {
                alert("Error!")
            }
        }
    );
}

function swapServeTeam() {
    if (waiting) return
    waiting = true
    fetch("/api/games/update/swapServeTeam", {
        method: "POST", body: JSON.stringify({
            id: id
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(
        (res) => {
            waiting = false
            if (res.ok) {
                location.reload()
            } else {
                alert("Error!")
            }
        }
    );
}

function swapPlayerSides(first) {
    if (waiting) return
    waiting = true
    fetch("/api/games/update/swapPlayerSides", {
        method: "POST", body: JSON.stringify({
            id: id,
            firstTeam: first
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(
        (res) => {
            waiting = false
            if (res.ok) {
                location.reload()
            } else {
                alert("Error!")
            }
        }
    );
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