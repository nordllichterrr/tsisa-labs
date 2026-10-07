from pulp import LpProblem, LpVariable, LpMaximize, LpStatus, value

n_skor = 600
n_pass = 300

prob = LpProblem("Trains", LpMaximize)
x = LpVariable("Skory", lowBound=0, cat='Integer')
y = LpVariable("Pass", lowBound=0, cat='Integer')

prob += n_skor*x + n_pass*y, "Passengers"
prob += x + y <= 5, "Bagazh"
prob += x <= 6, "Pocht"
prob += 8*x + 4*y <= 43, "Plackart"
prob += 4*x + y <= 32, "Kupe"

prob.solve()
print("Статус:", LpStatus[prob.status])
print(f"Скорых = {int(value(x))}, Пассажирских = {int(value(y))}")
print(f"Макс. пассажиров = {value(prob.objective)}")
