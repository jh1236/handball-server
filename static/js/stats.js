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

function addStatsButton(category = null, value = null) {
    let div = document.getElementById("args")
    let lbl = document.createElement("label")
    if (category === null) {
        category = document.getElementById("stats").value
    }
    lbl.textContent = "Where " + category + " of "
    let obj = document.createElement("input")
    let removeBtn = document.createElement("button")
    let selectScopeBtn = document.createElement("select")
    let hiddenBtn = document.createElement("input")
    let selectComparerBtn = document.createElement("select")
    removeBtn.textContent = "-"
    removeBtn.type = "button"
    removeBtn.onclick = () => removeStat(removeBtn)

    obj.type = "text"
    obj.className = "value"
    obj.name = category
    hiddenBtn.type = "checkbox"
    hiddenBtn.className = "isHidden"
    hiddenBtn.name = "hidden"
    let absolute = false
    let marked = false
    let compare = "="
    if (value) {
        value = value.replace("&gt;", ">").replace("&lt;", "<")
        if (value[0] === "$") {
            value = value.substring(1)
            hiddenBtn.checked = true
        }
        if (value[0] === "^") {
            value = value.substring(1)
        }
        marked = value.length > 0 && value[0] === "~"
        if (marked) {
            value = value.substring(1)
        }
        absolute = value.length > 1 && (value[0] === value[1] || value[0] === "=")
        if (absolute) {
            value = value.substring(1)
        }
        if (['>','<','!'].includes(value[0])) {
            compare = value[0]
            value = value.substring(1)
        }
        obj.value = value
    }
    selectScopeBtn.className = "scope"
    for (const s in scopes) {
        let opt = document.createElement("option")
        opt.textContent = scopes[s]
        opt.value = s
        selectScopeBtn.append(opt)
        if ((absolute && s === "every") || (marked && s === "specific") || (!absolute && !marked && s === "any")) {
            opt.selected = true
        }
    }

    selectComparerBtn.className = "comparer"
    for (const s in comparer) {
        let opt = document.createElement("option")
        opt.textContent = comparer[s]
        opt.value = s
        selectComparerBtn.append(opt)
        if (s === compare) {
            opt.selected = true
        }
    }
    lbl.append(selectScopeBtn)
    lbl.append(selectComparerBtn)
    lbl.append(obj)
    lbl.append(" hidden: ")
    lbl.append(hiddenBtn)
    lbl.append(removeBtn)
    lbl.append(document.createElement("br"))
    div.append(lbl)
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
    console.log(div.children)
    for (const i in div.children) {
        let lbl = div.children[i]
        let scope = null
        let hidden = null
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
            } else if (child.className === "isHidden") {
                hidden = child.checked;
            }
            if (scope !== null && comparer !== null && name !== null && hidden !== null) break;
        }
        if (scope == null) break;
        let toAdd = name + "="
        if (hidden) {
            toAdd += "$"
        }
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
    // console.log("/find?" + newAddr.join("&"))
}
