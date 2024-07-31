# -*- coding: utf-8 -*-
# Support for combination of temperature sensors
#
# Copyright (C) 2023  Michael Jäger <michael@mjaeger.eu>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import math
import typing as t

import numpy as np

REPORT_TIME = 0.300


class SavitzkyGolaySmoother:
    """
    Simplified Savitzky Golay Filter to only do smoothing
    """

    def __init__(self, order: int, smooth_time: float) -> None:
        # Determine the self._values/frame lengtht
        frame_length = max(
            order,
            math.ceil(smooth_time / REPORT_TIME),
        )

        # Frame length needs to be odd
        if frame_length % 2 == 0:
            frame_length += 1

        if frame_length < order + 2:
            raise TypeError("smooth_time is too short for the polynomials order")

        self.frame_length = frame_length
        self.window_length = (frame_length - 1) // 2

        # self._values tracking
        self._values = np.array([0.0] * frame_length)

        # Smoothing only
        self.coeff_m = np.linalg.pinv(
            np.mat(
                [
                    [k**i for i in range(order + 1)]
                    for k in range(-self.window_length, self.window_length + 1)
                ]
            )
        ).A[0]

    def reset(self, temp: float) -> None:
        self._values = np.tile([temp], self.frame_length)

    def update(self, temp: float) -> None:
        self._values[:-1] = self._values[1:]
        self._values[-1] = temp

    def smooth(self) -> t.List[float]:
        pad_left = self._values[0] - np.abs(
            self._values[1 : self.window_length + 1][::-1] - self._values[0]
        )
        pad_right = self._values[-1] + np.abs(
            self._values[-self.window_length - 1 : -1][::-1] - self._values[-1]
        )

        return list(
            np.convolve(
                self.coeff_m[::-1],
                np.concatenate((pad_left, self._values, pad_right)),
                mode="valid",
            )
        )


class PrinterSensorSmoothed:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.name = config.get_name().split()[-1]
        # ensure compatibility with itself
        self.sensor = self
        # set default values
        self.last_temp = self.min_temp = self.max_temp = 0.0
        # add object
        self.printer.add_object("temperature_smoothed " + self.name, self)

        # get sensor names
        self.unsmoothed_sensor_name = config.get("sensor_name")
        # get empty list for sensors, could be any sensor class or a heater
        self.unsmoothed_sensor = None

        # setup the smoother
        self.smoother = SavitzkyGolaySmoother(
            order=config.getint("smooth_order", 2, minval=0),
            smooth_time=config.getfloat("smooth_time", 1.0, above=0),
        )

        # time-controlled sensor update
        self.temperature_update_timer = self.reactor.register_timer(
            self._temperature_update_event
        )
        self.printer.register_event_handler("klippy:connect", self._handle_connect)
        self.printer.register_event_handler("klippy:ready", self._handle_ready)

    def _handle_connect(self):
        sensor = self.printer.lookup_object(self.unsmoothed_sensor_name)
        # check if sensor has get_status function and
        # get_status has a 'temperature' value
        if hasattr(sensor, "get_status") and "temperature" in sensor.get_status(
            self.reactor.monotonic()
        ):
            self.unsmoothed_sensor = sensor
        else:
            raise self.printer.config_error(
                "'%s' does not report a temperature." % self.unsmoothed_sensor_name
            )

    def _handle_ready(self):
        # Initialize the smoother values
        sensor_status = self.unsmoothed_sensor.get_status(self.reactor.monotonic())

        # Reset the smoother with the current temperature
        self.smoother.reset(temp=sensor_status["temperature"])

        # Start temperature update timer
        self.reactor.update_timer(
            self.temperature_update_timer,
            self.reactor.NOW,
        )

    def setup_minmax(self, min_temp, max_temp):
        self.min_temp = min_temp
        self.max_temp = max_temp

    def setup_callback(self, temperature_callback):
        self.temperature_callback = temperature_callback

    def get_report_time_delta(self):
        return REPORT_TIME

    def apply_smoothing(self):
        values = self.smoother.smooth()
        return round(values[-1], 2)

    def update_temp(self, eventtime):
        sensor_status = self.unsmoothed_sensor.get_status(eventtime)
        self.smoother.update(sensor_status["temperature"])

        temp = self.apply_smoothing()
        if temp:
            self.last_temp = temp

    def get_temp(self, eventtime):
        return self.last_temp, 0.0

    def get_status(self, eventtime):
        return {
            "temperature": round(self.last_temp, 2),
        }

    def _temperature_update_event(self, eventtime):
        # update sensor value
        self.update_temp(eventtime)

        # check min / max temp values
        if self.last_temp < self.min_temp:
            self.printer.invoke_shutdown(
                "SMOOTHED SENSOR temperature %0.1f "
                "below minimum temperature of %0.1f."
                % (
                    self.last_temp,
                    self.min_temp,
                )
            )
        if self.last_temp > self.max_temp:
            self.printer.invoke_shutdown(
                "SMOOTHED SENSOR temperature %0.1f "
                "above maximum temperature of %0.1f."
                % (
                    self.last_temp,
                    self.max_temp,
                )
            )

        # this is copied from temperature_host to enable time triggered updates
        # get mcu and measured / current(?) time
        mcu = self.printer.lookup_object("mcu")
        measured_time = self.reactor.monotonic()
        # convert to print time?! for the callback???
        self.temperature_callback(
            mcu.estimated_print_time(measured_time), self.last_temp
        )
        # set next update time
        return measured_time + REPORT_TIME


def load_config(config):
    pheaters = config.get_printer().load_object(config, "heaters")
    pheaters.add_sensor_factory("temperature_smoothed", PrinterSensorSmoothed)
