function runPassword() {
    let input = document.getElementById("pword")
    document.location.href = window.location.href.split('?')[0] + '?key=' + input.value
}