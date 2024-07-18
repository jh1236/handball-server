let id = 0

let setup = (newId, newSwapped) => {
    id = newId
    teamsSwapped = newSwapped
}
let best = ""
setBest = (i, s) => {
    best = i
    console.log(best)
    document.getElementById("rename").textContent = "Fairest And Best: " + s
}


function back() {
    document.location = `/games/${id}/edit`
}

function finish() {
    const protestOne = document.getElementById("protest0").checked ? document.getElementById("protestNotes0").value : null
    const protestTwo = document.getElementById("protest1").checked ? document.getElementById("protestNotes1").value : null
    fetch("/api/games/update/end", {
        method: "POST",
        body: JSON.stringify({
            id: id,
            bestPlayer: best,
            notes: document.getElementById("notes").value,
            protestTeamOne: protestOne,
            protestTeamTwo: protestTwo
        }),
        headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(
        (res) => {
            if (res.status === 204) {
                document.location.href = `/games/` + id
            } else {
                alert("Error!")
            }
        }
    );
}


function myFunction(button) {
    button.parentElement.getElementsByClassName("dropdown-content")[0].classList.toggle("show")
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

window.onload = () => {
    document.getElementById("protest0").onchange = () => {
        if (document.getElementById("protest0").checked) {
            document.getElementById("protestNotes0").style.display = "inline"
        } else {
            document.getElementById("protestNotes0").style.display = "none"
        }
    }
    document.getElementById("protest1").onchange = () => {
        if (document.getElementById("protest1").checked) {
            document.getElementById("protestNotes1").style.display = "inline"
        } else {
            document.getElementById("protestNotes1").style.display = "none"
        }
    }
}// Close the dropdown menu if the user clicks outside of it
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