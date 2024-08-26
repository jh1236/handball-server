function runPassword() {
    let user_id = document.getElementById("user_id").value
    let password = document.getElementById("password").value
    // let agree = document.getElementById("agree").checked
    // if (!agree) {
    //     alert("You have not agreed to the use of cookies and code of conduct!")
    //     return
    // }
    if (!user_id) {
        alert("You have not entered a user id!")
        return
    }
    if (!password) {
        alert("You have not entered a password!")
        return
    }

    //go to /api/login with user_id and password in post body
    fetch("/api/login", {
        method: "POST",
        body: JSON.stringify({
            "user_id": user_id,
            "password": password
        }),
        headers: {
            "Content-Type": "application/json"
        }
    }).then((res) => {
        if (res.status === 200) {
            window.location.reload()
        } else {
            alert("Incorrect password!")
        }
    })
}
