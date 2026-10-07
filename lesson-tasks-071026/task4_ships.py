from pulp import LpProblem, LpVariable, LpMinimize, LpStatus, value

prob = LpProblem("Ships", LpMinimize)
x1 = LpVariable("Burevestnik", 0, None, cat='Integer')
x2 = LpVariable("Albatros",   0, None, cat='Integer')
x3 = LpVariable("Chaika",     0, None, cat='Integer')

prob += 10*x1 + 8*x2 + 5*x3, "Zatraty"
prob += 3000*x1 + 2000*x2 + 1000*x3 >= 10000, "Pass"
prob += 20000*x1 + 12000*x2 + 7000*x3 <= 70000, "Fuel"
prob += 350*x1 + 250*x2 + 100*x3 <= 1100, "Crew"

prob.solve()
print("Статус:", LpStatus[prob.status])
print(f"Буревестник={int(value(x1))}, Альбатрос={int(value(x2))}, Чайка={int(value(x3))}")
print(f"Мин. затраты = {value(prob.objective)} млн руб.")
