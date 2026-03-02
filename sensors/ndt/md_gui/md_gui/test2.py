import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt


def analyze_gaussian_approximation(data, subset_size=30, n_subsets=10):
    metrics = []

    for _ in range(n_subsets):
        # Randomly sample a subset of the data
        subset = np.random.choice(data, size=subset_size, replace=False)

        # Perform the Shapiro-Wilk test
        shapiro_stat, shapiro_p = stats.shapiro(subset)

        # Perform the Kolmogorov-Smirnov test against a normal distribution
        ks_stat, ks_p = stats.kstest(subset, 'norm', args=(np.mean(subset), np.std(subset)))

        # Store metrics
        metrics.append({
            'shapiro_stat': shapiro_stat,
            'shapiro_p': shapiro_p,
            'ks_stat': ks_stat,
            'ks_p': ks_p,
            'is_gaussian': shapiro_p > 0.05 and ks_p > 0.05
        })

        # Optional: Plot the histogram and the fitted Gaussian
        plt.hist(subset, bins=15, density=True, alpha=0.5, color='g')
        xmin, xmax = plt.xlim()
        x = np.linspace(xmin, xmax, 100)
        p = stats.norm.pdf(x, np.mean(subset), np.std(subset))
        plt.plot(x, p, 'k', linewidth=2)
        plt.title('Subset Histogram and Fitted Gaussian')
        plt.show()

    return pd.DataFrame(metrics)


# Example usage
if __name__ == "__main__":
    # Generate some example data
    np.random.seed(42)
    data = np.random.normal(loc=0, scale=1, size=1000)  # Normally distributed data

    # Analyze subsets
    result = analyze_gaussian_approximation(data, subset_size=30, n_subsets=10)
    print(result)
