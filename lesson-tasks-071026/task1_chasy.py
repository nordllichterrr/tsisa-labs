from pulp import LpProblem, LpVariable, LpMaximize, LpStatus, value

prob = LpProblem("Chasy", LpMaximize)

x1 = LpVariable("Vanil", lowBound=0, cat='Integer')
x2 = LpVariable("Prezident", lowBound=0, cat='Integer')

prob += 1500*x1 + 2100*x2, "Vyruchka"
prob += 50*x1 + 40*x2 <= 1500, "Zoloto"
prob += 30*x1 + 50*x2 <= 1800, "Platina"

prob.solve()
print("Статус:", LpStatus[prob.status])
print(f"Ваниль = {int(value(x1))}, Президент = {int(value(x2))}")
print(f"Максимальная выручка = {value(prob.objective)}")
