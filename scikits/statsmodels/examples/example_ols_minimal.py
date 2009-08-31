"""Example: minimal OLS

"""

import numpy as np
import scikits.statsmodels as sm

nsample = 100
x = np.linspace(0,10, 100)
X = sm.tools.add_constant(np.column_stack((x, x**2)))
beta = np.array([1, 0.1, 10])
y = np.dot(X, beta) + np.random.normal(size=nsample)

results = sm.OLS(y, X).fit()
print results.summary()




