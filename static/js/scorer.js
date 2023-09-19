id = 0
setId = newId => id = newId

function score(firstTeam, firstPlayer) {
    fetch("/api/games/update/score", {
        method: "POST", body: JSON.stringify({
            id: id, firstTeam: firstTeam, firstPlayer: firstPlayer, ace: false
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => location.reload());
}

function ace(firstTeam) {
    fetch("/api/games/update/ace", {
        method: "POST", body: JSON.stringify({
            id: id, firstTeam: firstTeam,
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => location.reload());
}


function card(firstTeam, firstPlayer, color) {
    fetch("/api/games/update/card", {
        method: "POST", body: JSON.stringify({
            id: id, firstTeam: firstTeam, firstPlayer: firstPlayer, color: color, time: 3
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => location.reload());
}

function timeout(firstTeam) {
    fetch("/api/games/update/timeout", {
        method: "POST", body: JSON.stringify({
            id: id, firstTeam: firstTeam,
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => location.reload());
}

function fault(firstTeam) {
    fetch("/api/games/update/fault", {
        method: "POST", body: JSON.stringify({
            id: id, firstTeam: firstTeam,
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => location.reload());
}

function undo() {
    fetch("/api/games/update/undo", {
        method: "POST", body: JSON.stringify({id: id}), headers: {
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