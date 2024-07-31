# Smoothing temperature sensors for Klipper

These plugins implement two different flavors of a smoothing temperatur sensor for Klipper.

The [sgolay](./sgolay/) implementation in using a Savitzky Golay filter to implement the smoothing, the [whittaker-eilers](./whittaker-eilers/) version is using a Whittaker-Eilers Smoother

## Which one should I pck

The Whittaker-Eilers Smoother (WES) and Savitzky-Golay (SG) filter are both used for smoothing noisy data, but they have different approaches and benefits:

Benefits of Whittaker-Eilers Smoother over Savitzky-Golay filter:

1. WES is better at preserving the shape and location of peaks and troughs in the data, whereas SG can flatten or shift them.
2. WES adapts the smoothing level based on the data's noise level, whereas SG uses a fixed window size.
3. WES is more robust to outliers and anomalies, whereas SG can be affected by extreme values.
4. WES allows for different smoothing levels for different parts of the data, whereas SG applies uniform smoothing.

However, SG filters have their own strengths, such as:

1. SG filters are generally faster to compute.
2. SG filters have a straightforward implementation.
3. SG filters excel at removing uniform noise.

When smoothing noisy temperature sensor readings, the Whittaker-Eilers Smoother (WES) is the preferred method. However, WES requires additional Python modules, whereas the Savitzky-Golay (SG) filter offers a standalone solution, which streamlines the installation process.

## Installation

1. Download the `temperature_smoothing.py` of the implementation you want to use.
2. Copy the file onto your Raspberry Pi into the `~/klipper/extras/` directory.
3. Add the following section to your printer.cfg to load the plugin:

   ```ini
   [temperature_smoothing]
   ```

4. For the Whittaker-Eilers implementation run the following command on your Raspberry Pi using SSH:

   ```bash
   ~/klippy-env/bin/pip3 install whittaker-eilers
   ```

5. Restart Klipper to activate the plugin:

   ```bash
   sudo systecmctl restart klipper
   ```

## Using a smoothed temperature sensor

Your existing temperature sensor name should be prefixed with an underscore (`_`) to hide it from the UI but keep it as a data source for smoothing. Then add a new temperature sensor utilizing the smoothing plugin:

```ini

# Hidden temperature sensor that provides the raw readings
[temperature_sensor _Chamber]
sensor_type: Generic 3950 Airtemp
sensor_pin: T3
min_temp: 0
max_temp: 100

# Smoothed temperature sensor
[temperature_sensor Chamber]
sensor_type: temperature_smoothed
sensor_name: temperature_sensor _Chamber    # The unsmoothed sensor from above
smooth_time: 5.0                            # Smoothing window in seconds 
min_temp: 0     
max_temp: 100
```

### Optional: Tuning knobs for the Savitzky-Golay implementation

**`smooth_order`**
Controls the number of neighboring data points considered when calculating the smoothed value. A higher order results in smoother curves and greater noise reduction. The default values is **2**.

Typical order values for Savitzky Golay filters are:

- Order 1: Linear interpolation (minimal smoothing)
- Order 2: Quadratic polynomial (balanced smoothing)
- Order 3: Cubic polynomial (more aggressive smoothing)

### Optional: Tuning knobs for the Savitzy-Golay implementation

**`smooth_order`**
Determines the degree of smoothing applied to the data. It controls the number of iterations or passes the algorithm makes over the data to remove noise and smooth the signal. A higher order value increases the amount of smoothing and reduces noise more aggressively. The default value is **2**.

Typical order values range from 1 to 5, with:

- Order 1: Minimal smoothing, mostly preserving the original signal
- Order 2-3: Balanced smoothing, suitable for most applications
- Order 4-5: Aggressive smoothing, for very noisy data or specific use cases

**`smooth_lambda`**
Regulates the "strength" of the smoothing. A suitable lambda value depends on the data's noise level, desired smoothing level, and importance of preserving signal features. A higher lambda value results in more aggressive smoothing and greater noise reduction by favoring a smoother curve over fidelity of the data. The default values is **20000**.

Typical lambda values::

- <10000: Light smoothing, preserving most signal features
- <50000: Balanced smoothing, suitable for most applications
- \>50000: Aggressive smoothing, for very noisy data or specific use cases

## License

This work is licensed under the GNU General Public License v3.0, for more details check the [LICENSE](../LICENSE).
