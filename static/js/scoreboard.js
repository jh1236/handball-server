let id = 0
let tournament = ""

let updateCount = 0

let startTime = 0

let isUmpireTimeout = false

let startTimeServe = 0
let setup = (newId, change_id) => {
    id = newId
    updateCount = change_id
}
setTournament = t => tournament = t

let t = 1

function rotate(obj, angle) {
    let s = "rotate(" + angle + "deg)";
    obj.style.MozTransform = s
    obj.style.WebkitTransform = s;
    obj.style.OTransform = s;
    obj.style.MSTransform = s;
    obj.style.transform = s;
}

let time = null

function deleteFireworks() {
    function a() {
        let l = Array.from(document.getElementsByClassName("bigger"))
        for (let i of l) {
            console.log(i)
            i.width = Math.pow(1.2, (t / 40) * (t / 40))
            i.height = Math.pow(1.2, (t / 40) * (t / 40))
        }
        l = Array.from(document.getElementsByClassName("rotate"))
        for (let i of l) {
            rotate(i, t)
        }
        t++
        if (l) {
            setTimeout(a, 10)
        }
    }

    a()
    setTimeout(() => {
        let l = Array.from(document.getElementsByClassName("fireworks"))
        for (let i of l) {
            i.remove()
        }
    }, 5000)
}

function main(timeIn = null) {
    if (timeIn !== null) {
        time = timeIn
        console.log(time)
    }
    fetch(`/api/games/change_code?id=${id}`, {
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
    if (time > 0) {
        let date = new Date(0)
        date.setSeconds((Date.now() / 1000 - time))
        document.getElementById("elapsed").textContent = date.toISOString().substring(14, 19)
        console.log(Date.now() - time)
    } else if (time < 0) {
        let date = new Date(0)
        date.setSeconds(Math.abs(time))
        document.getElementById("elapsed").textContent = date.toISOString().substring(14, 19)
    } else {
        document.getElementById("elapsed").textContent = "00:00"
    }

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
    const dot1 = document.getElementById("dot1")
    const dot2 = document.getElementById("dot2")
    if (timeIn > 0) {
        startTime = timeIn
        isUmpireTimeout = Date.now() > timeIn
        if (isUmpireTimeout) {
            dot1.style.opacity = 1
        }
    }
    if (isUmpireTimeout) {
        document.getElementById("timeout").textContent = "Timeout"
        document.getElementById("timeout").style = 'font-size: 200pt; color: #FF9122'
        dot1.style.color = ""
        dot2.style.color = ""
        let temp = dot1.style.opacity
        dot1.style.opacity = dot2.style.opacity
        document.getElementById("dot2").style.opacity = temp
        console.log(temp)
        setTimeout(timeout, 1000) //one seconds
    } else {
        let clock = (startTime - Date.now()) / 1000
        document.getElementById("timeout").textContent = clock.toFixed(1)
        if (clock > 0) {
            setTimeout(timeout, 10)
            document.getElementById("timeout").style = ""
        } else {
            if (dot1.style.opacity === dot2.style.opacity) {
                dot1.style.opacity = 1
            }
            let temp = dot1.style.opacity
            dot1.style.opacity = dot2.style.opacity
            dot2.style.opacity = temp
            document.getElementById("timeout").textContent = "0.0"
            document.getElementById("timeout").style.color = "#FF2222"
            dot1.style.backgroundColor = "#FF2222"
            dot2.style.backgroundColor = "#FF2222"
            setTimeout(timeout, 1000) //two seconds
        }
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
