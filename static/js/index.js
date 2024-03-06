function logout() {
    document.cookie.split(";").forEach(function (c) {
        document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
    });
    if (location.toString().includes("admin")) {
        document.location = location.toString().replace("/admin", "")
    } else {
        location.reload()
    }


}

let load = (s, admin = false) => {
    let masterDiv = document.getElementById("navBar")
    let navDiv = document.createElement("div")
    let userDiv = document.createElement("div")
    masterDiv.append(userDiv)
    masterDiv.append(navDiv)
    navDiv.style = "position: fixed;top: 2%;left: 2%;right:100%;white-space:nowrap;"
    navDiv.style.zIndex = "100"
    userDiv.style = "top: 0%;left: 0%;width:100%;white-space:nowrap;height:20pxmargin-left: auto;margin-right: 0;"
    userDiv.style.backgroundColor = getComputedStyle(masterDiv).getPropertyValue("--color-bg")
    userDiv.style.zIndex = "99"
// Add User info




// Add Logo
    let para = document.createElement("p")
    let a = document.createElement('a');
    let image = document.createElement("img")
    if (admin) {
        a.href = "/" + s + "admin"
    } else {
        a.href = "/" + s
    }
    if (s) {
        image.src = `/api/tournaments/image?name=${s.replace("/", "")}`
    } else {
        image.src = "/api/image?name=SUSS"
    }
    image.className = "logo"
    a.append(image)
    para.append(a)
    para.append(document.createElement("br"))
    a = document.createElement('a');
    image = document.createElement("img")
    a.href = "/" + s
    image.src = "/api/image?name=SUSS_2"
    image.className = "logo2"
    a.append(image)
    para.append(a)
    navDiv.append(para)


    //Add NavBar
    function addToNavBar(display, link, hasAdmin) {
        let h = document.createElement('h2')
        h.append(document.createTextNode(display))
        h.className = "nav"
        let a2 = document.createElement('a');
        if (admin && hasAdmin) {
            a2.href = link + "/admin"
        } else {
            a2.href = link
        }
        a2.style = "text-decoration: none;color: inherit;"
        a2.append(h)
        para.append(a2)
        return h
    }

    // addToNavBar(s, `/${s}/`).style = "font-style: italic;font-size: 18px"
    addToNavBar("Home", `/`, false)
    if (s) {
        addToNavBar("Fixtures", `/${s}fixtures`, true)
    } else {
        addToNavBar("Sign-Up", `/signup`, true)
    }
    addToNavBar("Teams", `/${s}teams`, true)
    addToNavBar("Ladder", `/${s}ladder`, false)
    addToNavBar("Players", `/${s}players/`, true)
    addToNavBar("Officials", `/${s}officials`, false)
    addToNavBar("Documents", "/documents", false)
    if (document.cookie.includes("userName")) {
        addToNavBar(document.cookie.split("userName=")[1].split(";")[0].replaceAll('"',""),"/user")
    } else {
        addToNavBar("Log In", "/user")
    }
    var toInsert = document.createElement("div");
    toInsert.innerHTML = "©2023 Squarers' United Sporting Syndicate. All rights reserved.";
    toInsert.style.position = "absolute";
    toInsert.style.bottom = "0px";
    toInsert.style.width = "100%";
    toInsert.style.textAlign = "center";
}