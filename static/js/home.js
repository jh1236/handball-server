function newRound(tournament) {
    fetch('/api/games/update/round', {
        method: 'POST', body: JSON.stringify({
            tournament: tournament.replace('/', '')
        }), headers: {
            'Content-type': 'application/json; charset=UTF-8'
        }
    }).then(() => location.reload());
}