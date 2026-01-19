def is_stable_array(matrix):
    n = len(matrix)
    diagonal1_product = 1
    diagonal2_product = 1

    for i in range(n):
        diagonal1_product *= matrix[i][i]
        diagonal2_product *= matrix[i][n - i - 1]

    if abs(diagonal1_product - diagonal2_product) <= 50:
        return "Yes"
    else:
        return "No"

# Input matrix size
n = int(input("Enter the size of the matrix (2 ≤ n ≤ 10): "))

# Input matrix elements
matrix = []
for i in range(n):
    row = []
    for j in range(n):
        element = int(input(f"Enter element at position ({i+1}, {j+1}): "))
        row.append(element)
    matrix.append(row)

# Check if the array is stable
result = is_stable_array(matrix)

# Print the result
print(result)