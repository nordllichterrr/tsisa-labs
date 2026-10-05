import networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

edges = [
    ("v1", "v2", 17),
    ("v1", "v4", 37),
    ("v1", "v3", 18),
    ("v2", "v5", 33),
    ("v2", "v4", 16),
    ("v3", "v4", 18),
    ("v3", "v6", 33),
    ("v4", "v5", 16),
    ("v4", "v6", 17),
    ("v5", "v7", 24),
    ("v6", "v7", 22),
    ("v3", "v7", 55),
]

start, finish = "v1", "v7"

G = nx.DiGraph()
for u, v, w in edges:
    G.add_edge(u, v, weight=w)

topo = list(nx.topological_sort(G))

dp = {node: float("-inf") for node in G.nodes()}
dp[start] = 0
parent = {start: None}

for node in topo:
    if dp[node] == float("-inf"):
        continue
    for _, nxt, data in G.out_edges(node, data=True):
        candidate = dp[node] + data["weight"]
        if candidate > dp[nxt]:
            dp[nxt] = candidate
            parent[nxt] = node

path = []
node = finish
while node is not None:
    path.append(node)
    node = parent[node]
path.reverse()

max_weight = dp[finish]

print("Максимальный путь:", " -> ".join(path))
print("Суммарный вес:", max_weight)

pos = {
    "v1": (0, 0),
    "v2": (1, 1.5),
    "v3": (1, -1.5),
    "v4": (2, 0),
    "v5": (3, 1.5),
    "v6": (3, -1.5),
    "v7": (4, 0),
}

path_edges = set(zip(path, path[1:]))

plt.figure(figsize=(12, 7))
for u, v, w in edges:
    if (u, v) in path_edges:
        color, lw, style = "green", 3, "-"
    else:
        color, lw, style = "gray", 1.5, "--"
    plt.annotate("", xy=pos[v], xytext=pos[u],
                 arrowprops=dict(arrowstyle="->", color=color, lw=lw, linestyle=style))
    mx = (pos[u][0] + pos[v][0]) / 2
    my = (pos[u][1] + pos[v][1]) / 2
    plt.text(mx, my + 0.08, str(w), fontsize=11, color=color, ha="center")

for node, (x, y) in pos.items():
    if node in (start, finish):
        c = "lightgreen"
    elif node in path:
        c = "lightyellow"
    else:
        c = "lightblue"
    plt.scatter(x, y, s=1500, c=c, zorder=3, edgecolors="black", linewidths=2)
    plt.text(x, y, node, fontsize=14, fontweight="bold", ha="center", va="center", zorder=4)

plt.title(f"Максимальный путь {start} -> {finish}: {' -> '.join(path)} (вес = {max_weight})")
plt.axis("off")
plt.tight_layout()
plt.savefig("variant_15_max_path.png", dpi=150, bbox_inches="tight")
print("Граф сохранён: variant_15_max_path.png")
