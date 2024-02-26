function sortTable(id, n, fix = true) {
    let table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
    table = document.getElementById("sort" + id);
    switching = true;
    // Set the sorting direction to ascending:
    rows = table.rows;
    if (n >= 0) {
        x = rows[1].getElementsByTagName("TD")[n].innerHTML;
    } else {
        x = rows[1].getElementsByTagName("TH")[1].innerHTML;
    }
    if (!isNaN(x) || x === "-" || x.endsWith("%")) {
        dir = "desc";
    } else {
        dir = "asc"
    }
    /* Make a loop that will continue until
    no switching has been done: */
    let lastX;
    let lastY;
    while (switching) {
        // Start by saying: no switching is done:
        rows = table.rows;
        switching = false;
        length = rows[0].getElementsByTagName("TH").length

        /* Loop through all table rows (except the
        first, which contains table headers): */
        for (i = 1; i < (rows.length - 1); i++) {
            // Start by saying there should be no switching:
            shouldSwitch = false;
            /* Get the two elements you want to compare,
            one from current row and one from the next: */
            if (n >= 0) {
                x = rows[i].getElementsByTagName("TD")[n].innerHTML;
                y = rows[i + 1].getElementsByTagName("TD")[n].innerHTML;
            } else {
                x = rows[i].getElementsByTagName("TH")[1].innerHTML;
                y = rows[i + 1].getElementsByTagName("TH")[1].innerHTML;
            }
            if (x.endsWith("%")) {
                x = x.slice(0, -1)
            }
            if (y.endsWith("%")) {
                y = y.slice(0, -1)
            }
            if (x === "-") {
                x = -1
            }
            if (y === "-") {
                y = -1
            }
            if (!isNaN(x)) {
                x = Number(x)
                y = Number(y)
            } else {
                x = x.toLowerCase()
                y = y.toLowerCase()
            }
            lastX = rows[i].getElementsByTagName("TD")[(length - 3)].innerHTML
            lastY = rows[i + 1].getElementsByTagName("TD")[(length - 3)].innerHTML
            if (!isNaN(lastX)) {
                lastX = Number(lastX)
                lastY = Number(lastY)
            } else {
                lastX = lastX.toLowerCase()
                lastY = lastY.toLowerCase()
            }
            /* Check if the two rows should switch place,
            based on the direction, asc or desc: */
            if (dir === "asc") {
                if (x > y) {
                    // If so, mark as a switch and break the loop:
                    shouldSwitch = true;
                    break;
                }
                if (x === y && lastX > lastY) {
                    shouldSwitch = true;
                    break;
                }
            } else if (dir === "desc") {
                if (x < y) {
                    // If so, mark as a switch and break the loop:
                    shouldSwitch = true;
                    break;
                }
                if (x === y && lastX < lastY) {
                    shouldSwitch = true;
                    break;
                }
            }
        }
        if (shouldSwitch) {
            /* If a switch has been marked, make the switch
            and mark that a switch has been done: */
            rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
            switching = true;
            // Each time a switch is done, increase this count by 1:
            switchcount++;
        } else {
            /* If no switching has been done AND the direction is "asc",
            set the direction to "desc" and run the while loop again. */
            let testAgainst
            if (!isNaN(x)) {
                testAgainst = "desc";
            } else {
                testAgainst = "asc"
            }
            if (switchcount === 0 && dir === testAgainst) {
                if (!isNaN(x)) {
                    dir = "asc";
                } else {
                    dir = "desc"
                }
                switching = true;
            }
        }
    }
    for (let i = 0; i < rows[0].getElementsByTagName("TH").length - 1; i++) {
        rows[0].getElementsByTagName("TH")[i + 1].style.color = ""
    }
    let testAgainst
    if (!isNaN(x)) {
        testAgainst = "desc";
    } else {
        testAgainst = "asc"
    }
    if (dir === testAgainst) {
        rows[0].getElementsByTagName("TH")[n +( fix ? 2 : 1)].style.color = "#33ac33"
    } else {
        rows[0].getElementsByTagName("TH")[n + (fix ? 2 : 1)].style.color = "#ac3333"
    }
}