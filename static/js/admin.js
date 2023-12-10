let id = -1
let tournament = ""
let setId = (newId) => id = Number(newId)
let setTournament = t => tournament = t
function resolveGame() {
    fetch("/api/games/update/resolve", {
        method: "POST",
        body: JSON.stringify({
            id: id,
            tournament: tournament.replace("/", ""),
        }),
        headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(() => location.reload());
}