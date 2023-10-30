let id = 0
let tournament = ""

let updateCount = 0

let setup = (newId, change_id) => {
    id = newId
    updateCount = change_id
}
setTournament = t => tournament = t

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
        setTimeout(main, 2000)
    }
}

function swap() {
    if (document.location.href.includes("swap")) {
        document.location.href = window.location.href.replace("swap=true", "").replaceAll("?", "")
    } else {
        document.location.href = window.location.href + "?swap=true"
    }
}