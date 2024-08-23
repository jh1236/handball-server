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
    alert(password+" "+user_id)

    
    //go to /api/login with user_id and password in post body
    fetch("/api/login/check", {
        method: "POST",
        body: JSON.stringify({
            "user_id": user_id,
            "password": password
        }),
        headers: {
            "Content-Type": "application/json"
        }
    }).then((res) => {
        res.json().then(
            o => {
                if (o.success) { s
                    alert("success")
                    document.location.href = "/"
                } else {
                    alert("Invalid user id or password!")
                }
            }
        )
    })
    alert("what the fuck");

    // document.location.href = window.location.href.split('?')[0] + '?key=' + input.value
}
