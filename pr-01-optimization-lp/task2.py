from scipy.optimize import linprog

c = [-50, -30]

A_ub = [
    [2, 1],
    [3, 2],
    [0, 1]
]
b_ub = [6, 10, 2]

bounds = [(0, None), (0, None)]

result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')

print("="*60)
print("Задача №2: Производство красок")
print("="*60)
print(f"Статус: {result.message}")
print(f"\nОптимальный выпуск (т):")
print(f"  Краска №1: {result.x[0]:.2f}")
print(f"  Краска №2: {result.x[1]:.2f}")
print(f"\nМаксимальная прибыль: {result.fun * (-1):.2f} тыс.руб.")

used_pigment = 2*result.x[0] + 1*result.x[1]
used_olifa = 3*result.x[0] + 2*result.x[1]
print(f"\nИспользование ресурсов:")
print(f"  Пигмент: {used_pigment:.2f} / 6 т")
print(f"  Олифа: {used_olifa:.2f} / 10 т")
print(f"  Спрос на №2: {result.x[1]:.2f} / 2 т")
