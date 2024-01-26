function setColor(color, id) {
    colors = ["Blue", "Green", "Purple", "Black", "Brown"]
    document.getElementById(id).textContent = color
    if (color === "None/Unknown") {
        document.getElementById(id).style.backgroundColor = ""
    } else {
        document.getElementById(id).style.backgroundColor = color
    }
    if (colors.includes(color)) {
        document.getElementById(id).style.color = "white"
    } else {
        document.getElementById(id).style.color = ""
    }
}


function submit() {
    if (!document.getElementById("coc").checked) {
        alert("You have not agreed to the code of conduct!")
        return
    }
    let umpires = []
    for (let i = 0; i < 3; i++) {
        if (document.getElementById(`umpire${i+1}`).checked) {
            umpires.push(document.getElementById(`name${i+1}`).value)
        }
    }
    fetch("/api/signup", {
        method: "POST",
        body: JSON.stringify({
            teamName: document.getElementById("teamName").value,
            playerOne: document.getElementById("name1").value,
            playerTwo: document.getElementById("name2").value,
            substitute: document.getElementById("name3").value,
            colorOne: document.getElementById("primary").textContent,
            colorTwo: document.getElementById("secondary").textContent,
            umpires: umpires
        }),
        headers: {
            "Content-type": "application/json; charset=UTF-8"
        }
    }).then(
        (res) => {
            if (res.status === 204) {
                document.location.href = "/"
            } else {
                alert("Error!")
            }
        });
}