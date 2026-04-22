"""
1 Euro Filter - Adaptive Low-Pass Filter for Human-Computer Interaction
Based on the paper: "1€ Filter: A Simple Speed-based Low-pass Filter for
Noisy Input in Interactive Systems" by Géry Casiez et al. (2012)

This filter dynamically adjusts smoothing based on signal velocity:
  - Slow movements → heavy smoothing (eliminates hand tremors)
  - Fast movements → light smoothing (preserves responsiveness)
"""

import math
import time


class LowPassFilter:
    """Simple first-order low-pass filter."""
    
    def __init__(self, alpha=1.0):
        self.__raw_value = 0.0
        self.__filtered_value = 0.0
        self.__alpha = alpha
        self.__initialized = False
    
    def filter(self, value, alpha=None):
        if alpha is not None:
            self.__alpha = alpha
        if not self.__initialized:
            self.__filtered_value = value
            self.__initialized = True
        else:
            self.__filtered_value = self.__alpha * value + (1.0 - self.__alpha) * self.__filtered_value
        self.__raw_value = value
        return self.__filtered_value
    
    @property
    def value(self):
        return self.__filtered_value
    
    def reset(self):
        self.__initialized = False


class OneEuroFilter:
    """
    1 Euro Filter for smoothing noisy real-time signals.
    
    Parameters:
        freq:       Expected signal frequency in Hz (e.g., camera FPS)
        min_cutoff: Minimum cutoff frequency. Lower = smoother but more lag.
        beta:       Speed coefficient. Higher = less lag during fast moves.
        d_cutoff:   Derivative cutoff frequency. Usually left at 1.0.
    """
    
    def __init__(self, freq=30.0, min_cutoff=1.0, beta=0.007, d_cutoff=1.0):
        self.freq = freq
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.__x_filter = LowPassFilter()
        self.__dx_filter = LowPassFilter()
        self.__last_time = None
    
    @staticmethod
    def __alpha(cutoff, freq):
        tau = 1.0 / (2.0 * math.pi * cutoff)
        te = 1.0 / freq
        return 1.0 / (1.0 + tau / te)
    
    def filter(self, x, timestamp=None):
        """
        Filter a noisy value.
        
        Args:
            x: The raw noisy measurement
            timestamp: Current time in seconds (auto-generated if None)
        
        Returns:
            The filtered (smoothed) value
        """
        if timestamp is None:
            timestamp = time.time()
        
        if self.__last_time is not None and timestamp != self.__last_time:
            self.freq = 1.0 / (timestamp - self.__last_time)
        self.__last_time = timestamp
        
        # Estimate velocity (derivative)
        prev_x = self.__x_filter.value
        dx = (x - prev_x) * self.freq if self.__x_filter.value != 0 else 0.0
        
        # Filter the derivative
        edge = self.__alpha(self.d_cutoff, self.freq)
        edx = self.__dx_filter.filter(dx, edge)
        
        # Dynamic cutoff based on speed
        cutoff = self.min_cutoff + self.beta * abs(edx)
        
        # Filter the signal
        alpha = self.__alpha(cutoff, self.freq)
        return self.__x_filter.filter(x, alpha)
    
    def reset(self):
        """Reset filter state (call when starting a new stroke)."""
        self.__x_filter.reset()
        self.__dx_filter.reset()
        self.__last_time = None
