from structure import manageGame

if __name__ == '__main__':
    manageGame.create_tournament("Test", "RoundRobin", "BasicFinals",
                                 True, True, True, [52, 13, 40, 4, 28, 22, 26], [1, 2, 3, 4, 9])
