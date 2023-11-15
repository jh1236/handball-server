let id = 0
let tournament = ""
let teamsSwapped = false
let teamName = ""
let startTime = -1
let setup = (newId, newSwapped) => {
    id = newId
    teamsSwapped = newSwapped
}
setTournament = t => tournament = t

function swap() {
    if (document.location.href.includes("swap")) {
        document.location.href = window.location.href.replace("swap=true", "").replaceAll("&", "")
    } else {
        document.location.href = window.location.href + "&swap=true"
    }
}


let lxor = (a, b) => a ? !b : b

let timeoutTime = -1

function score(firstTeam, firstPlayer) {
    fetch("/api/games/update/score", {
        method: "POST", body: JSON.stringify({
            id: id,
            firstTeam: lxor(Boolean(firstTeam), teamsSwapped),
            tournament: tournament.replace("/", ""),
            firstPlayer: firstPlayer,
            ace: false
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => location.reload());
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
    }).then(() => location.reload());
}

function ace() {
    fetch("/api/games/update/ace", {
        method: "POST", body: JSON.stringify({
            id: id,
            tournament: tournament.replace("/", "")
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => location.reload());
}


function card(firstTeam, firstPlayer, color) {
    fetch("/api/games/update/card", {
        method: "POST", body: JSON.stringify({
            id: id,
            tournament: tournament.replace("/", ""),
            firstTeam: lxor(Boolean(firstTeam), teamsSwapped),
            firstPlayer: firstPlayer,
            color: color, time: 3
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => location.reload());
}


let firstPlayerSelected = true
let firstTeamSelected = true

function selectTwo() {
    firstPlayerSelected = false
    document.getElementById("nameTwo").style = "color:green;"
    document.getElementById("nameOne").style = "color:white;"
}

function selectOne() {
    firstPlayerSelected = true
    document.getElementById("nameTwo").style = "color:white;"
    document.getElementById("nameOne").style = "color:green;"
}


let added = false

function openCustomCard(firstTeam, playerOne, playerTwo) {
    firstTeamSelected = firstTeam
    document.getElementById("nameOne").textContent = playerOne
    document.getElementById("nameTwo").textContent = playerTwo
    document.getElementById("cardSelect").style.width = "100%";
    document.getElementById("duration").value = "4"
    document.getElementById("durationText").textContent = "Duration (4)"
    window.scrollTo(0, 0);
    window.onscroll = function () {
        window.scrollTo(0, 0);
    };
    if (!added) {
        added = true
        console.warn("found!")
        document.getElementById("duration").addEventListener("input", (event) => {
            document.getElementById("durationText").textContent = `Duration (${event.target.value})`;
        });
    }
}

function sendCustomCard() {
    fetch("/api/games/update/card", {
        method: "POST", body: JSON.stringify({
            id: id,
            tournament: tournament.replace("/", ""),
            firstTeam: lxor(firstTeamSelected, teamsSwapped),
            firstPlayer: firstPlayerSelected,
            color: "yellow",
            time: +(document.getElementById("duration").value) % 10
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => location.reload());
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
    serveClock(Date.now() + 10000)
    fetch("/api/games/update/serve_clock", {
        method: "POST", body: JSON.stringify({
            id: id,
            start: true,
            tournament: tournament.replace("/", ""),
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    });
}

function stopServeClock() {
    startTime = -1
    document.getElementById("serveBtn").style = ""
    document.getElementById("serveBtn").textContent = "Start Serve Timer"
    fetch("/api/games/update/serve_clock", {
        method: "POST", body: JSON.stringify({
            id: id,
            start: false,
            tournament: tournament.replace("/", ""),
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
            tournament: tournament.replace("/", ""),
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