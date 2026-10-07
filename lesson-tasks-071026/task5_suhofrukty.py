from pulp import LpProblem, LpVariable, LpMaximize, LpStatus, value

prob = LpProblem("Suhofrukty", LpMaximize)
y1 = LpVariable("Mix1", 0, None, cat='Continuous')
y2 = LpVariable("Mix2", 0, None, cat='Continuous')

prob += 40*y1 + 50*y2, "Dohod"
prob += 0.25*y1 + 0.25*y2 <= 2.8, "Anis"
prob += 0.75*y1 + 0.25*y2 <= 4.5, "Shtreyfling"
prob += 0.5*y2 <= 3.0, "Grushi"

prob.solve()
print("Статус:", LpStatus[prob.status])
print(f"Смесь 1 = {value(y1):.4f}, Смесь 2 = {value(y2):.4f}")
print(f"Макс. доход = {value(prob.objective):.4f} руб.")
