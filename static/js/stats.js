const scopes = {"any": "any player ", "every": "every player ", "specific": "a specific player "}
const comparer = {"=": "is equal to ", "!": "is not equal to ", ">": " is greater than ", "<": "is less than "}

function reloadGraph(tournament) {
    let x = document.getElementById("x-axis").value
    let y = document.getElementById("y-axis").value
    let player = location.toString().split("/players/")[1].split("/")[0]
    if (tournament) {
        tournament = tournament.replaceAll("/", "")
        document.getElementById("graph").src = `/graphs/game_player?x=${x}&y=${y}&player=${player}&tournament=${tournament}`
    } else {
        document.getElementById("graph").src = `/graphs/game_player?x=${x}&y=${y}&player=${player}`
    }

}

function addStatsButton() {
    let div = document.getElementById("args")
    let lbl = document.createElement("label")
    lbl.textContent = "Where " + document.getElementById("stats").value + " of "
    let obj = document.createElement("input")
    let removeBtn = document.createElement("button")
    let selectScopeBtn = document.createElement("select")
    selectScopeBtn.className = "scope"
    for (const s in scopes) {
        let opt = document.createElement("option")
        opt.textContent = scopes[s]
        opt.value = s
        selectScopeBtn.append(opt)
    }
    let selectComparerBtn = document.createElement("select")
    selectComparerBtn.className = "comparer"
    for (const s in comparer) {
        let opt = document.createElement("option")
        opt.textContent = comparer[s]
        opt.value = s
        selectComparerBtn.append(opt)
    }
    lbl.append(selectScopeBtn)
    lbl.append(selectComparerBtn)
    removeBtn.textContent = "-"
    removeBtn.type = "button"
    removeBtn.onclick = () => removeStat(removeBtn)
    lbl.append(obj)
    lbl.append(removeBtn)
    lbl.append(document.createElement("br"))
    div.append(lbl)
    obj.type = "text"
    obj.className = "value"
    obj.name = document.getElementById("stats").value
}

function removeStat(button) {
    let child = button.parentElement
    let parent = child.parentElement
    console.warn(this.parent)
    parent.removeChild(child)
}

function processLookup() {
    let div = document.getElementById("args")
    let newAddr = []
    for (const i in div.children) {
        let lbl = div.children[i]
        let scope = null
        let name = null
        let val = null
        let comparer = null
        for (const j in lbl.childNodes) {
            let child = lbl.childNodes[j]
            if (child.className === "scope") {
                scope = child.value
            } else if (child.className === "comparer") {
                comparer = child.value
            } else if (child.className === "value") {
                name = child.name
                val = child.value
            }
            if (scope !== null && comparer !== null && name !== null) break;
        }
        if (scope == null) break;
        let toAdd = name + "="
        if (scope === "all") {
            toAdd += comparer
        } else if (scope === "specific") {
            toAdd += "~"
        }
        if (comparer!== "=") {
            toAdd += comparer
        }
        toAdd += val
        console.log(toAdd)
        newAddr.push(toAdd)
    }
    document.location = "/find?" + newAddr.join("&")
}
