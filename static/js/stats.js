function reloadGraph(tournament) {
    let x = document.getElementById("x-axis").value
    let y = document.getElementById("y-axis").value
    player = location.toString().split("/players/")[1].split("/")[0]
    if (tournament) {
        tournament = tournament.replaceAll("/","")
        document.getElementById("graph").src = `/graphs/game_player?x=${x}&y=${y}&player=${player}&tournament=${tournament}`
    } else {
        document.getElementById("graph").src = `/graphs/game_player?x=${x}&y=${y}&player=${player}`
    }

}