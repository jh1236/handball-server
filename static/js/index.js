let load = (s) => {
    let div = document.getElementById("navBar")
    div.style = "position: fixed;top: 2%;left: 2%;right:100%;white-space:nowrap;"

// Add Logo
    let para = document.createElement("p")
    let a = document.createElement('a');
    let image = document.createElement("img")
    a.href = "/" + s
    if (s) {
        image.src = `/api/tournaments/image?name=${s.replace("/","")}`
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
    div.append(para)


    //Add NavBar
    function addToNavBar(display, link) {
        let h = document.createElement('h2')
        h.append(document.createTextNode(display))
        h.className = "nav"
        let a2 = document.createElement('a');
        a2.href = link
        a2.style = "text-decoration: none;color: inherit;"
        a2.append(h)
        para.append(a2)
        return h
    }

    // addToNavBar(s, `/${s}/`).style = "font-style: italic;font-size: 18px"
    addToNavBar("Home", `/`)
    if (s) {
        addToNavBar("Fixtures", `/${s}fixtures`)
    }
    addToNavBar("Teams", `/${s}teams`)
    addToNavBar("Ladder", `/${s}ladder`)
    addToNavBar("Players", `/${s}players`)
    addToNavBar("Officials", `/${s}officials`)
    addToNavBar("U.Q.P.", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    addToNavBar("Rules", "/rules")
    addToNavBar("Conduct", "/code_of_conduct")
}