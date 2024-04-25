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
    let sortBtn = document.createElement("input")
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
    sortBtn.type = "checkbox"
    sortBtn.className = "sort"
    sortBtn.name = "hidden"
    sortBtn.onclick = click_sort
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
            sortBtn.checked = true
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
    lbl.append(" sort: ")
    lbl.append(sortBtn)
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

function click_sort() {
    let div = document.getElementById("args")
    for (const i of document.getElementsByClassName("sort")) {
        if (i === this) continue;
        i.checked = false
    }
}

function processLookup() {
    let div = document.getElementById("args")
    let newAddr = []
    console.log(div.children)
    for (const i of div.children) {
        let scope = null
        let hidden = null
        let sort = null
        let name = null
        let val = null
        let comparer = null
        for (const j of i.childNodes) {

            if (j.className === "scope") {
                scope = j.value
            } else if (j.className === "comparer") {
                comparer = j.value
            } else if (j.className === "value") {
                name = j.name
                val = j.value
            } else if (j.className === "isHidden") {
                hidden = j.checked;
            } else if (j.className === "sort") {
                sort = j.checked;
            }
            if (scope !== null && comparer !== null && name !== null && hidden !== null && sort !== null) break;
        }
        if (scope == null) break;
        let toAdd = name + "="
        if (hidden) {
            toAdd += "$"
        }
        if (sort) {
            toAdd += "^"
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
