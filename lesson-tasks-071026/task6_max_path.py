from pulp import LpProblem, LpVariable, LpMaximize, LpStatus, value
import networkx as nx

edges = {
    ('A','B'):4, ('A','C'):2, ('B','C'):5, ('B','D'):10,
    ('C','E'):3, ('E','D'):4, ('D','F'):11,
}
nodes = ['A','B','C','D','E','F']
s, t = 'A', 'F'

prob = LpProblem("MaxPath", LpMaximize)
x = {e: LpVariable(f"x_{e[0]}{e[1]}", cat='Binary') for e in edges}

prob += sum(edges[e]*x[e] for e in edges), "PathWeight"

for n in nodes:
    out_ = sum(x[e] for e in edges if e[0]==n)
    in_  = sum(x[e] for e in edges if e[1]==n)
    if n == s:
        prob += out_ - in_ == 1, f"flow_{n}"
    elif n == t:
        prob += out_ - in_ == -1, f"flow_{n}"
    else:
        prob += out_ - in_ == 0, f"flow_{n}"

prob.solve()
print("Статус:", LpStatus[prob.status])
chosen = [e for e in edges if value(x[e]) > 0.5]
print("Выбранные дуги:", chosen)
print("Максимальный вес =", value(prob.objective))

G = nx.DiGraph()
for (u,v),w in edges.items():
    G.add_edge(u,v,weight=w)
print("Проверка (nx):", nx.dag_longest_path(G, weight='weight'))
