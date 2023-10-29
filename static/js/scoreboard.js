let id = 0
let tournament = ""

let updateCount = 0

let setup = (newId, change_id) => {
    id = newId
    updateCount = change_id
}
setTournament = t => tournament = t

function main() {
    setInterval(async () => {
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
    }, 2000)
}