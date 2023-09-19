let div = document.getElementById("navBar")
div.style = "position: fixed;top: 2%;left: 2%;right:100%;white-space:nowrap;"

// Add Logo
let para = document.createElement("p")
let a = document.createElement('a');
let image = document.createElement("img")
image.style = "display:inline"
a.href = "/"
image.src = "/api/teams/image?name=SUSS"
image.className = "logo"
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
}

addToNavBar("Home", "/")
addToNavBar("Teams", "/teams")
addToNavBar("Ladder", "/ladder")
addToNavBar("Players", "/players")
addToNavBar("Officials", "/officials")
addToNavBar("U.Q.P.", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
addToNavBar("Rules", "/rules")
addToNavBar("Code Of Conduct", "/code_of_conduct")