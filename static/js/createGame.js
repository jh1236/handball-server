let id = 0
let tournament = "";
let teamsSwapped = false

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
                        document.location.href = `/games/` + o.id + "/edit"
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
                        document.location.href = `/games/` + o.id + "/edit"
                    }
                )
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
}

window.onload = () => {
    if (window.location.href.includes("create_players")) {
        for (let t = 1; t <= 2; t++) {
            for (let p = 1; p <= 3; p++) {
                console.log(`searchP${p}T${t}`)
                let elem = document.getElementById(`searchP${p}T${t}`)
                elem.onkeyup = (e) => {
                    for (let i of document.getElementById(`P${p}T${t}`).children) {
                        if (i.id.startsWith("search")) continue
                        let value = e.target.value.toLowerCase()
                        i.style.display = !value || i.textContent.toLowerCase().includes(value) ? "block" : "none"
                    }
                }
            }
        }
    } else {
        for (let t = 1; t <= 2; t++) {
            let elem = document.getElementById(`searchT${t}`)
            elem.onkeyup = (e) => {
                for (let i of document.getElementById(`T${t}`).children) {
                    if (i.id.startsWith("search")) continue
                    let value = e.target.value.toLowerCase()
                    i.style.display = !value || i.textContent.toLowerCase().includes(value) ? "block" : "none"
                }
            }

        }
    }


}