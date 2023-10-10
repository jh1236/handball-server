let id = 0
let tournament = ""
setId = newId => id = newId
setTournament = t => tournament = t

let timeoutTime = -1

function score(firstTeam, firstPlayer) {
    fetch("/api/games/update/score", {
        method: "POST", body: JSON.stringify({
            id: id,
            firstTeam: Boolean(firstTeam),
            tournament: tournament.replace("/", ""),
            firstPlayer: firstPlayer,
            ace: false
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => location.reload());
}

function ace(firstTeam) {
    fetch("/api/games/update/ace", {
        method: "POST", body: JSON.stringify({
            id: id,
            firstTeam: firstTeam,
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
            firstTeam: Boolean(firstTeam),
            firstPlayer: firstPlayer,
            color: color, time: 3
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => location.reload());
}

function timeout(firstTeam) {
    timeoutTime = Date.now() + 30000
    document.getElementById("myNav").style.width = "100%";
    window.onscroll = function () {
        window.scrollTo(0, 100);
    };
    setInterval(function (x) {
        if (timeoutTime < 0) {
            window.onscroll = function () {
            };
            document.getElementById("myNav").style.width = "0%";
            return
        } else if (timeoutTime - Date.now() < 0) {
            document.getElementById("timeoutClock").style = "color:red;"
        } else {
            document.getElementById("timeoutClock").style = ""
        }
        document.getElementById("timeoutClock").textContent = "" + Math.round((timeoutTime - Date.now()) / 100) / 10
    }, 100)

    fetch("/api/games/update/timeout", {
        method: "POST", body: JSON.stringify({
            id: id, firstTeam: firstTeam,
            tournament: tournament.replace("/", ""),
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    });
}


function fault(firstTeam) {
    fetch("/api/games/update/fault", {
        method: "POST", body: JSON.stringify({
            id: id, firstTeam: firstTeam,
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