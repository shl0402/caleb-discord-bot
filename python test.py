import pandas as pd

# Creating DataFrames
df = pd.DataFrame({
    'col1': [1, 2, 3, 4, 5, 6, 7, 8],
    'col2': ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'],
    'col3': [10, 20, 30, 40, 50, 60, 70, 80]
})

# Basic Operations
print("\nFirst 5 rows:")
print(df.head())

print("\nShape (rows, columns):")
print(df.shape)

print("\nDataFrame Info:")
df.info()

print("\nStatistical Summary:")
print(df.describe())

print("\nColumn Names:")
print(df.columns)

print("\nData Types:")
print(df.dtypes)

# Selection Examples
print("\nSelecting single column 'col1':")
print(df['col1'])

print("\nSelecting multiple columns:")
print(df[['col1', 'col2']])
print(df.loc[:,['col1', 'col2']])

print("test")
print(df.loc[[0,5],["col1"]])
print("???")

print("\nSelecting first row:")
print(df.iloc[0])

print("\nSelecting rows 0-4 and columns 0-1:")
print(df.iloc[0:5, 0:2])

# Filtering Examples
print("\nFiltering rows where col1 > 5:")
print(df[df['col1'] > 5])

# Grouping Example
print("\nGrouping by col2 and calculating mean:")
print(df.groupby('col2').mean())

# Sorting Example
print("\nSorting by col1:")
print(df.sort_values('col1'))

# Adding some missing values for demonstration
df.loc[0, 'col3'] = None
print("\nChecking missing values:")
print(df.isna())

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

# NumPy Examples
print("NUMPY DEMONSTRATIONS:")
print("\nCreating arrays:")
arr1d = np.array([1, 2, 3, 4, 5])
arr2d = np.array([[1, 2, 3], [4, 5, 6]])
print("1D array:", arr1d)
print("2D array:\n", arr2d)

print("\nArray operations:")
print("Add 1 to all elements:", arr1d + 1)
print("Multiply by 2:", arr1d * 2)
print("Mean:", np.mean(arr1d))
print("Standard deviation:", np.std(arr1d))

print("\nReshaping:")
reshaped = arr1d.reshape(5, 1)
print("Reshaped to 5x1:\n", reshaped)

print("\nRandom numbers:")
random_arr = np.random.rand(3, 3)
print("Random 3x3 array:\n", random_arr)

# Matplotlib Examples
print("\nMATPLOTLIB DEMONSTRATIONS:")

# Generate sample data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Create multiple plots
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(10, 8))

# Line plot
ax1.plot(x, y)
ax1.set_title('Line Plot')
ax1.grid(True)

# Scatter plot
ax2.scatter(x[::10], y[::10])
ax2.set_title('Scatter Plot')

# Bar plot
ax3.bar(range(5), np.random.rand(5))
ax3.set_title('Bar Plot')

# Histogram
ax4.hist(np.random.randn(1000))
ax4.set_title('Histogram')

plt.tight_layout()
plt.show()

# Scikit-learn Examples
print("\nSCIKIT-LEARN DEMONSTRATIONS:")

# Generate sample dataset
np.random.seed(42)
X = np.random.rand(100, 1) * 10
y = 2 * X + 1 + np.random.randn(100, 1) * 2

# Split the data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print("Training set shape:", X_train.shape)
print("Test set shape:", X_test.shape)

# Train linear regression model
model = LinearRegression()
model.fit(X_train, y_train)

# Make predictions
y_pred = model.predict(X_test)

# Evaluate model
mse = mean_squared_error(y_test, y_pred)
r2_score = model.score(X_test, y_test)

print("\nModel Results:")
print("Mean Squared Error:", mse)
print("R-squared Score:", r2_score)
print("Model Coefficient:", model.coef_[0][0])
print("Model Intercept:", model.intercept_[0])

# Visualize the regression results
plt.figure(figsize=(8, 6))
plt.scatter(X_test, y_test, color='blue', label='Actual Data')
plt.plot(X_test, y_pred, color='red', label='Regression Line')
plt.xlabel('X')
plt.ylabel('y')
plt.title('Linear Regression Results')
plt.legend()
plt.grid(True)
plt.show()