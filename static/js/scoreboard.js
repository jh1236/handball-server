let id = 0
let tournament = ""

let updateCount = 0

let startTime = 0

let startTimeServe = 0
let setup = (newId, change_id) => {
    id = newId
    updateCount = change_id
}
setTournament = t => tournament = t

function deleteFireworks() {
    setTimeout(() => {
        let l = Array.from(document.getElementsByClassName("fireworks"))
        for (let i of l) {
            console.log(i)
            i.remove()
        }
    }, 5000)
}

function main() {
    fetch(`/api/games/change_code?id=${id}&tournament=${tournament.replace("/", "")}`, {
        method: "GET"
    }).then((res) => {
        res.json().then(
            o => {
                if (updateCount !== Number(o.code)) {
                    document.location.reload()
                }
            }
        )
    });
    if (updateCount >= 0) {
        setTimeout(main, 1000)
    }
}

function swap() {
    if (document.location.href.includes("swap")) {
        document.location.href = window.location.href.replace("swap=true", "").replaceAll("?", "")
    } else {
        document.location.href = window.location.href + "?swap=true"
    }
}

function jump() {
    new_id = +(document.getElementById("jump").value)
    console.log(new_id)
    document.location.href = `/${tournament}games/${new_id}/display`
}


function timeout(timeIn = 0) {
    console.log(timeIn)
    if (timeIn > 0) {
        startTime = timeIn
    }
    let clock = (startTime - Date.now()) / 1000
    document.getElementById("timeout").textContent = clock.toFixed(1)
    if (clock > 0) {
        setTimeout(timeout, 10)
        document.getElementById("timeout").style = ""
    } else {
        document.getElementById("timeout").textContent = "0.0"
        document.getElementById("timeout").style.color = "#FF2222"
    }
}

function serveClock(timeIn = 0) {
    if (timeIn > 0) {
        startTimeServe = timeIn
    }
    let clock = (startTimeServe - Date.now()) / 1000
    if (clock > 0) {
        document.getElementById("serveClock").style.color = "#FFFFFF"
        document.getElementById("serveClock").textContent = clock.toFixed(1)
    } else {
        document.getElementById("serveClock").textContent = "0.0"
        document.getElementById("serveClock").style.color = "#FF0000"
    }
    if (clock > -3) {
        setTimeout(serveClock, 10)
    } else {
        document.getElementById("serveClock").textContent = "0.0"
        document.getElementById("serveClock").style.color = "#000000"
    }
}
