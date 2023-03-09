import numpy as np


class Functions:
    class Normal:
        def __init__(self, mu, sigma):
            self.mu = mu
            self.sigma = sigma

        def __call__(self, x):
            return (
                1
                / (self.sigma * np.sqrt(2 * np.pi))
                * np.exp(-((x - self.mu) ** 2) / (2 * self.sigma**2))
            )

    class Sigmoid:
        def __init__(self, mu, sigma):
            self.mu = mu
            self.sigma = sigma

        def __call__(self, x):
            return 1 / (1 + np.exp(-(x - self.mu) / self.sigma))
