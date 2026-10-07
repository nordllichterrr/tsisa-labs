import networkx as nx

edges = [
    (1,2,0.1,8),(1,3,0.1,5),
    (2,4,0.1,10),(2,5,0.06,10),
    (3,5,0.08,12),(3,6,0.08,4),
    (4,7,0.14,10),(4,8,0.11,7),
    (5,8,0.12,9),(5,9,0.08,7),
    (6,9,0.08,15),(6,10,0.08,6),
    (7,11,0.15,12),(8,11,0.16,10),
    (8,12,0.12,10),(9,12,0.12,10),
    (9,13,0.1,18),(10,13,0.1,18),
    (11,14,0.16,12),(12,14,0.1,14),
    (12,15,0.15,10),(13,15,0.16,8),
    (14,16,0.2,10),(15,16,0.08,15),
]

G = nx.DiGraph()
for u,v,f,t in edges:
    G.add_edge(u,v,fuel=f,time=t)

all_paths = list(nx.all_simple_paths(G, 1, 16))
recs = []
for p in all_paths:
    f = sum(G[p[i]][p[i+1]]['fuel'] for i in range(len(p)-1))
    t = sum(G[p[i]][p[i+1]]['time'] for i in range(len(p)-1))
    recs.append((f, t, p))

pareto = []
for f,t,p in sorted(recs):
    if not any(f2<=f and t2<=t and (f2<f or t2<t) for f2,t2,_ in pareto):
        pareto.append((f,t,p))

print(f"Найдено Парето-оптимальных путей: {len(pareto)}")
for f,t,p in pareto:
    print(f"  топливо={f:.2f}, время={t} мин, путь: {' -> '.join(map(str,p))}")

print("\nМинимум по топливу:", min(recs, key=lambda r:r[0])[:2])
print("Минимум по времени:", min(recs, key=lambda r:r[1])[:2])
