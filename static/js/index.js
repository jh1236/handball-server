let div = document.getElementById("navBar")
div.style = "position: fixed;top: 2%;left: 2%;right:100%;white-space:nowrap;"

// Add Logo
let para = document.createElement("p")
let a = document.createElement('a');
let image = document.createElement("img")
image.style = "display:inline"
a.href = "http://handball-tourney.zapto.org/"
image.src = "http://handball-tourney.zapto.org/api/teams/image?name=SUSS"
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

addToNavBar("Home", "http://handball-tourney.zapto.org/")
addToNavBar("Ladder", "http://handball-tourney.zapto.org/ladder")
addToNavBar("Teams", "http://handball-tourney.zapto.org/teams")
addToNavBar("Officials", "http://handball-tourney.zapto.org/officials")
addToNavBar("Rules", "http://handball-tourney.zapto.org/rules")