function newRound(tournament) {
    fetch('/api/games/update/round', {
        method: 'POST', body: JSON.stringify({
            tournament: tournament.replace('/', '')
        }), headers: {
            'Content-type': 'application/json; charset=UTF-8'
        }
    }).then(() => location.reload());
}

function sendNotes(tournament) {
    fetch('/api/tournaments/note', {
        method: 'POST', body: JSON.stringify({
            tournament: tournament.replace('/', ''),
            note: document.getElementById("notes").value
        }), headers: {
            'Content-type': 'application/json; charset=UTF-8'
        }
    }).then(() => location.reload());
}