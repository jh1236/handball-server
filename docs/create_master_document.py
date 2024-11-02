IN_FILES = ["!Types", "Games", "Team", "Player", "Tournament", "Official", "Login"]

if __name__ == '__main__':
    out = ""
    for f in IN_FILES:
        fname = f
        if f.startswith("!"):
            fname = f[1:]
        else:
            fname += " Endpoints"
        fname += ".md"
        with open(fname, "r") as file:
            out += "\n"
            out += file.read()
    with open("master.md", "w+") as file:
        file.write(out)

