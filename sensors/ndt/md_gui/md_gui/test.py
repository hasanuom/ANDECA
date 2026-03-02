import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import shapiro, skew, kurtosis


# Function to check Gaussianity and provide measures of dissimilarity
def analyze_segment(data):
    if len(data) < 3:  # Shapiro-Wilk requires at least 3 samples
        return False, None, None, None

    stat, p_value = shapiro(data)
    skewness = skew(data)
    kurt = kurtosis(data)

    print(f'Statistics={stat:.3f}, p-value={p_value:.3g}, skewness={skewness:.3f}, kurtosis={kurt:.3f}')

    return stat, p_value, skewness, kurt


# Main class to process incoming data samples
class GaussianAnalyzer:
    def __init__(self, segment_size):
        self.segment_size = segment_size
        self.data = []
        self.stat = 0
        self.p_value = 0
        self.skewness = 0
        self.kurt = 0

    def add_sample(self, sample):
        self.data.append(sample)

        # If we exceed the segment size, remove the oldest sample
        if len(self.data) > self.segment_size:
            self.data.pop(0)

        # Check for Gaussianity if we have enough samples
        if len(self.data) == self.segment_size:
            self.stat, self.p_value, self.skewness, self.kurt = analyze_segment(self.data)

            # Plotting the histogram for visualization
            # plt.hist(self.data, bins=20, alpha=0.5)
            # plt.title('Current Segment Distribution')
            # plt.xlabel('Value')
            # plt.ylabel('Frequency')
            # plt.show()

# Example of using the GaussianAnalyzer
analyzer = GaussianAnalyzer(segment_size=100)
stats = []
p = []
skew_vals = []
kurt_vals = []

n_samples = 1000
samples = 5 + 0.1*np.random.random(n_samples)
# samples = 5 + 0.1*np.ones(n_samples)

N = 50
x = np.arange(0, 2*N)
gauss = np.exp(-(x-N)**2 / N)

samples[n_samples // 2:n_samples // 2+ 2*N] += gauss
for s in samples:
    analyzer.add_sample(s)
    stats.append(analyzer.stat)
    p.append(analyzer.p_value)
    skew_vals.append(analyzer.skewness)
    kurt_vals.append(analyzer.kurt)

p = np.array(p)
skew_vals = np.array(skew_vals)
kurt_vals = np.array(kurt_vals)

fig, ax = plt.subplots(6, sharex='all')
ax[0].plot(samples)
ax[1].plot(stats)
ax[2].plot(p)
ax[3].plot(skew_vals)
ax[4].plot(kurt_vals)
ax[5].plot(gauss)
plt.show()
