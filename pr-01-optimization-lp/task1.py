from scipy.optimize import linprog

c = [-380, -430, -460]

A_ub = [
    [0.4, 0.3, 0.2],
    [0.2, 0.3, 0.4],
    [0.05, 0.07, 0.1],
    [0.01, 0.05, 0.15]
]
b_ub = [20, 35, 7, 10]

bounds = [(0, None), (0, None), (0, None)]

result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')

print("="*60)
print("Задача №1: Производство клея")
print("="*60)
print(f"Статус: {result.message}")
print(f"\nОптимальный выпуск (кг):")
print(f"  Клей №1: {result.x[0]:.2f}")
print(f"  Клей №2: {result.x[1]:.2f}")
print(f"  Клей №3: {result.x[2]:.2f}")
print(f"\nМаксимальная стоимость: {result.fun * (-1):.2f} руб.")
