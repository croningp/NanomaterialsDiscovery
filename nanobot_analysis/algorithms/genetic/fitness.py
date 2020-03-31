import scipy
import scipy.stats
import numpy as np
import scipy.signal as sgl
from scipy.integrate import simps

# Threshold
WAVELENGTH_THRESHOLD = 650
ABSORBANCE_THRESHOLD = 0.3

# Rod regions area
TRANSVERSE_REGION = (490, 560)
MIDDLE_REGION = (580, 650)
LONG_REGION = (700, 800)

# Arrow head region area
OCTAHEDRON_REGION = (560, 640)
OCTAHEDRON_UNWANTED_REGION = (640, 720)

def _check_max_absorbance_above_cutoff(max_abs: float, threshold: float) -> bool:
    return max_abs >= threshold


### SPHERE FITNESS ###
def _check_no_peaks_after_wavelength_cutoff(x: np.array, y: np.array, threshold: float) -> bool:
    for wavelength, absorbance in zip(x, y):
        if wavelength >= WAVELENGTH_THRESHOLD:
            if absorbance >= threshold:
                return False

    return True

def maximise_single_peak(x, y, target_nm, sigma=20):
    """
    Rates how close an observed UV peak is from a specified target
    The closer the observed is to the target, the higher the fitness

    Args:
        x (List): Series of wavelength data from a UV spectrum
        y (List): Series of absorbance data from a UV spectrum
        target_nm (int): Target position in nm to aim for
        sigma (int): Standard deviation number?

    Returns:
        fitness (float): Fitness of the given data as a measure of distance from target
    """
    x = np.array(x)
    y = np.array(y)

    # Observed Peak
    largest_peak_pos = np.argmax(y)
    observed_peak_nm = x[largest_peak_pos]
    observed_peak_abs = y[largest_peak_pos]

    # Target Peak
    target_peak = np.argmin(np.abs(x - target_nm))
    target_peak_absorbance = y[target_peak]

    # Calculate the normal probability distribution
    ref = scipy.stats.norm(target_nm, sigma).pdf(target_nm)
    obs = scipy.stats.norm(target_nm, sigma).pdf(observed_peak_nm)

    # Fitness value
    fitness = (obs / float(ref)) + target_peak_absorbance

    # Check for bad absorbance
    if not _check_max_absorbance_above_cutoff(observed_peak_abs, 0.15):
        return 0.0

    # Check for values above wavelength cutoff
    threshold = observed_peak_abs * ABSORBANCE_THRESHOLD
    if not _check_no_peaks_after_wavelength_cutoff(x, y, threshold):
        return fitness * 0.7

    return fitness

### SPHERE FITNESS END ###


### ROD FITNESS ###

def calculate_region_area(
    x: np.array,
    y: np.array,
    start_nm: int,
    end_nm: int,
    dx: int = 1
) -> float:
    """Calculates the area under the spectrum curve in a certain region

    Args:
        x (list): Wavelengths
        y (list): Absorbances
        start_nm (int): Start of region
        end_nm (int): End of region
        dx (int, optional): Spacing of integration points. Defaults to 1.

    Returns:
        float: Area under the region
    """

    # Get all absorbance values in a range between start_nm and end_nm
    start, end = np.searchsorted(x, start_nm, "left"), np.searchsorted(x, end_nm, "right")
    target_y = np.array([y[i] for i in np.arange(start, end)])

    # Area beneath curve
    return simps(target_y, dx=dx)


def low_pass_filter(x: np.array, y: np.array, lp_freq: float = 10) -> np.array:
    """Uses a low pass filter to smooth out the data
    Authored by Yibin Jiang

    Args:
        x (np.array): Wavelengths
        y (np.array): Absorbances
        lp_freq (float, optional): Low pass filter frequency. Defaults to 15.

    Returns:
        np.array: Processed data
    """

    # Get the sampling frequency
    sampling_freq = x.shape[0]

    # Normalise the frequency
    normalised_freq = lp_freq / (sampling_freq / 2)

    # Create a butterworth filter - God knows what b and a actually are
    b, a = sgl.butter(5, normalised_freq, "low")

    # Apply digital filter forwards and backwords on data
    return sgl.filtfilt(b, a, y)


def rods_fitness(x: list, y: list) -> float:
    """Calculates the fitness for synthesising rods
    Calculates the area between certain ranges and divides the target areas
    Passes thourgh a series of filters to correct fitness to account for bad results

    Args:
        x (list): Wavelengths
        y (list): Absorbances

    Returns:
        float: Fitness value
    """
    x, y = np.array(x), np.array(y)
    min_y = y[np.argmin(y)]
    y -= min_y

    # Get transverse peak (left)
    transverse = calculate_region_area(x, y, *TRANSVERSE_REGION)

    # Get middle peak
    middle = calculate_region_area(x, y, *MIDDLE_REGION)

    # Get the rods peak
    long = calculate_region_area(x, y, *LONG_REGION)

    # Find all peaks
    y = low_pass_filter(x, y)
    peaks, _ = sgl.find_peaks(y)

    # Calculate fitness value
    fitness = long / (transverse + middle)

    print(f"Area of Transverse: {transverse}")
    print(f"Area of Middle region: {middle}")
    print(f"Area of Long: {long}")
    print(f"Total peaks: {len(peaks)}")
    print(f"Peak locations: {x[peaks]}")

    penalty_count = 0

    # Low absorbance, return 0
    if np.max(y) < 0.50:
        print(f"Penalty -- Below absorbance threshold -- 0% fitness")
        return 0

    # More than 4 peaks
    if len(peaks) >= 4:
        print(f"Penalty -- More than 4 peaks -- 0% fitness")
        return 0

    # Less than two peaks, 10% of calculated fitness
    if len(peaks) < 2:
        print(f"Penalty -- Less than two peaks -- 40% fitness")
        fitness *= 0.4
        penalty_count += 1

    # # Area of the rods is less than the transverse peak, fitness = 0
    if long < transverse:
        print(f"Penalty -- Long less than transverse -- 50% fitness")
        fitness *= 0.5
        penalty_count += 1

    # # Middle peak is greater than the transverse peak, 75% of calculated fitness
    if middle > transverse:
        print(f"Penalty -- Middle greater than transverse -- 75% fitness")
        fitness *= 0.75
        penalty_count += 1


    # 2 or more penalties, no bonus
    if penalty_count >= 2:
        return fitness

    # Well done, bonus
    return fitness * 1.5

### RODS FITNESS END ###

### OCTAHEDRON FITNESS ###
def octahedron_fitness(x: list, y: list) -> float:
    # Convert to array
    x, y = np.array(x), np.array(y)

    # Subtract lowest absorbance across the spectra
    min_y = y[np.argmin(y)]
    y -= min_y

    # Max NM
    max_nm = x[np.argmax(y)]

    # Get transverse peak (left)
    target_region = calculate_region_area(x, y, *OCTAHEDRON_REGION)

    # Get middle peak
    unwanted_region = calculate_region_area(x, y, *OCTAHEDRON_UNWANTED_REGION)

    # Find all peaks
    y = low_pass_filter(x, y)
    peaks, _ = sgl.find_peaks(y)

    # Calculate fitness value
    fitness = target_region / unwanted_region

    # Low absorbance, return 0
    if np.max(y) < ABSORBANCE_THRESHOLD:
        print(f"Penalty -- Below absorbance threshold -- 0% fitness")
        return 0

    # # Area of the rods is less than the transverse peak, fitness = 0
    if unwanted_region > target_region:
        print(f"Penalty -- Unwanted greater than target -- 0% fitness")
        return 0

    # More than 4 peaks
    if len(peaks) >= 2:
        print(f"Penalty -- More than 3 peaks -- 60% fitness")
        fitness *= 0.6

    return fitness
