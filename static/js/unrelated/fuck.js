const socket = io();
let players = []
socket.on('connect', function () {
    socket.emit('join', {userName: document.cookie.split("userName=")[1].split(';')[0].replaceAll('"', '')});
});
let timePlayed = Date.now()
let prevTimePlayed = Date.now()


setTimeout(timer, 10)

socket.on("game won", (event) => {
    alert(event.winner + " has won!!!")
})

socket.on("gamestate", (event) => {
    console.log(event)
    document.getElementById("oldBackground").style.backgroundColor = document.getElementById("background").style.backgroundColor
    document.getElementById("oldForeground").style.color = document.getElementById("foreground").style.color
    document.getElementById("oldForeground").textContent = document.getElementById("foreground").textContent
    document.getElementById("background").style.backgroundColor = event.bg_color
    document.getElementById("foreground").style.color = event.fg_color
    document.getElementById("foreground").textContent = event.text
    players = event.players.keys
    prevTimePlayed = Date.now() - timePlayed
    document.getElementById("oldTimer").textContent = Math.round((Date.now() - timePlayed) / 10) / 100
    timePlayed = Date.now()

    let p = document.getElementById("players")
    while (p.firstChild) {
        p.removeChild(p.lastChild);
    }
    for (let i in event.players) {
        let newElement = document.createElement('li')
        newElement.textContent = i + ": " + event.players[i]
        p.append(newElement)
    }
})

function correct() {
    socket.emit("next", {"correct": true})
}

function incorrect() {
    socket.emit("next", {"correct": false})
}

function disco() {
    socket.emit("disco")
}

function timer() {
    let time = Math.round((Date.now() - timePlayed) / 10) / 100
    document.getElementById("timer").textContent = time
    setTimeout(timer, 10)
    if (time > 3.00) {
        document.getElementById("timer").style.color = "#FF0000"
    } else {
        document.getElementById("timer").style.color = "#000000"
    }
}
