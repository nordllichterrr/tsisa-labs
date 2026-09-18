from scipy.optimize import linprog

c = [-480, -80]

A_ub = [
    [1, 1],
    [18, 14],
    [80, 40]
]
b_ub = [400, 6000, 22000]

bounds = [(0, None), (0, None)]

result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')

print("="*60)
print("Задача №3: Посев культур")
print("="*60)
print(f"Статус: {result.message}")
print(f"\nОптимальные площади (га):")
print(f"  Кукуруза: {result.x[0]:.2f}")
print(f"  Соя: {result.x[1]:.2f}")
print(f"  Всего: {result.x[0] + result.x[1]:.2f}")
print(f"\nМаксимальная прибыль: {result.fun * (-1):.2f} тыс.руб.")
