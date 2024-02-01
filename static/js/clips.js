let id = 0
let key = 0
let teamOutcome = 0
let personalOutcome = 0
let setup = (newId, newKey) => {
    id = newId
    key = newKey
}

setTeamOutcome = (outcome) => {
    document.getElementById("team").textContent = document.getElementById("team"+outcome).textContent
    teamOutcome = outcome
}

setPersonalOutcome = (outcome) => {
    document.getElementById("personal").textContent = document.getElementById("personal"+outcome).textContent
    personalOutcome = outcome
}


function bookmark() {
    fetch("/api/clip/bookmark", {
        method: "POST", body: JSON.stringify({
            key: key,
            id: id,
            reason: document.getElementById("reasonText").value
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => document.location.reload());
}

function submit() {
    if (!teamOutcome || !personalOutcome || !document.getElementById("tags").value || !document.getElementById("starring").value) {
        alert("The form is not complete!")
        return
    }
    fetch("/api/clip/rate", {
        method: "POST", body: JSON.stringify({
            key: key,
            id: id,
            certain: document.getElementById("certain").checked,
            teamOutcome: document.getElementById("team").textContent,
            personalOutcome: document.getElementById("personal").textContent,
            starring: document.getElementById("starring").value.replaceAll(",","|"),
            quality: +document.getElementById("quality").value,
            tags: document.getElementById("tags").value.replaceAll(",","|").replaceAll("\n",""),
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => document.location = "/video/unrated?key=" + key);
}

function garbage() {
    fetch("/api/clip/rate", {
        method: "POST", body: JSON.stringify({
            key: key,
            id: id,
            certain: false,
            teamOutcome: "garbage",
            personalOutcome: "garbage",
            starring: "garbage",
            quality: 0,
            tags: "garbage",
        }), headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => document.location = "/video/unrated?key=" + key);
}



function answer() {
    if (!teamOutcome || !personalOutcome) {
        alert("The form is not complete!")
        return
    }
    document.getElementById("teamOutcome").value = document.getElementById("team").textContent
    document.getElementById("personalOutcome").value =document.getElementById("personal").textContent
    document.getElementById("form").submit()
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