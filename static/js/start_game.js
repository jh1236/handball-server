id = 0
setId = newId => id = newId

let best = ""
setBest = (i, s) => {
    best = i
    document.getElementById("rename").textContent = "Fairest And Best: " + s
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
        body: JSON.stringify({id: id, firstTeamServed: first_serves, swapTeamOne: left, swapTeamTwo: right}),
        headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => location.reload());
}

function finish() {
    fetch("/api/games/update/end", {
        method: "POST",
        body: JSON.stringify({id: id, bestPlayer: best}),
        headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => document.location.href = "/games/" + id + "/");
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