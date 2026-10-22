#!/usr/bin/env python

############################################################################
#
# MODULE:       t.rast.stl2ca
# AUTHOR:       Paulo van Breugel
# PURPOSE:      Extracts the time series of two areas from the same
#               space-time raster dataset (strds), regularizes each onto an
#               evenly spaced axis, runs an STL decomposition
#               (seasonal / trend / remainder) on each and produces a
#               multi-panel plot comparing the two areas.
#
# COPYRIGHT:    (c) 2026 Paulo van Breugel and the GRASS Development Team
#               This program is free software under the GNU General Public
#               License (>=v2). Read the file COPYING that comes with GRASS
#               for details.
#
#############################################################################

# %module
# % description: STL decomposition (seasonal/trend/remainder) comparing the time series of two areas of the same strds
# % keyword: temporal
# % keyword: raster
# % keyword: time series
# % keyword: decomposition
# % keyword: STL
# % keyword: plot
# % keyword: display
# %end

# %option G_OPT_STRDS_INPUT
# % key: strds
# % guisection: Input
# %end

# %option G_OPT_M_COORDS
# % key: coordinates
# % required: no
# % label: Area 1: point coordinates (east,north)
# % description: Comma separated pair of map coordinates of the point to extract for area 1. In the GUI (launched from a Map Display) the value can be filled by clicking in the display. Mutually exclusive with 'zone' and 'raster'.
# % guisection: Area 1
# %end

# %option G_OPT_V_INPUT
# % key: zone
# % required: no
# % label: Area 1: vector map defining the sampling area
# % description: Vector map (points, lines or polygons) defining the area-1 sampling area. All features in the map are rasterized and pooled into a single sample; use v.extract beforehand to pre-select a subset of features. Mutually exclusive with 'coordinates' and 'raster'.
# % guisection: Area 1
# %end

# %option G_OPT_R_INPUT
# % key: raster
# % required: no
# % label: Area 1: raster map defining the sampling area
# % description: Raster map whose non-null cells define the area-1 sampling area; cell values are ignored. All non-null cells are pooled into a single sample. Mutually exclusive with 'coordinates' and 'zone'.
# % guisection: Area 1
# %end

# %option G_OPT_M_COORDS
# % key: coordinates2
# % required: no
# % label: Area 2: point coordinates (east,north)
# % description: Comma separated pair of map coordinates of the point to extract for area 2. Mutually exclusive with 'zone2' and 'raster2'.
# % guisection: Area 2
# %end

# %option G_OPT_V_INPUT
# % key: zone2
# % required: no
# % label: Area 2: vector map defining the sampling area
# % description: Vector map (points, lines or polygons) defining the area-2 sampling area, sampled the same way as 'zone'. Mutually exclusive with 'coordinates2' and 'raster2'.
# % guisection: Area 2
# %end

# %option G_OPT_R_INPUT
# % key: raster2
# % required: no
# % label: Area 2: raster map defining the sampling area
# % description: Raster map whose non-null cells define the area-2 sampling area, sampled the same way as 'raster'. Mutually exclusive with 'coordinates2' and 'zone2'.
# % guisection: Area 2
# %end

# %option
# % key: statistic
# % type: string
# % label: Pixel aggregation statistic
# % description: Statistic used to summarize the pixels within each area at each timestep, the same for both areas so the comparison is fair. 'mean', 'min' and 'max' use a single, cheap t.rast.univar call. 'median' and 'percentile' are more robust to outlier/contaminated pixels but require t.rast.univar's extended-statistics mode, which sorts all cell values in memory for each map; this is a real memory cost on very large rasters.
# % options: mean,median,min,max,percentile
# % answer: mean
# % required: no
# % guisection: Input
# %end

# %option
# % key: percentile_value
# % type: double
# % label: Percentile to use as the statistic
# % description: Percentile (0-100) summarizing the pixels within each area at each timestep. Only used when 'statistic' is 'percentile'.
# % options: 0-100
# % required: no
# % guisection: Input
# %end

# %option
# % key: frequency
# % type: string
# % label: Target resampling frequency
# % description: Pandas offset alias for the regular time axis the series is resampled onto, e.g. D (day), W (week), MS (month start), 16D (16 days). Required for absolute-time strds.
# % required: no
# % guisection: Regularization
# %end

# %option
# % key: step
# % type: integer
# % label: Relative-time step (override)
# % description: Integer spacing of the regular axis for relative-time STRDS, in the dataset's own time unit. If omitted, the dataset granularity (from t.info) is used and the extent is taken from the data. Ignored for absolute-time STRDS (use 'frequency' instead).
# % required: no
# % guisection: Regularization
# %end

# %option
# % key: interpolation
# % type: string
# % label: Gap interpolation method
# % description: Method passed to pandas Series.interpolate() to fill gaps after resampling.
# % options: linear,time,nearest,zero,slinear,quadratic,cubic,spline,polynomial,pchip,akima
# % answer: linear
# % required: no
# % guisection: Regularization
# %end

# %option
# % key: order
# % type: integer
# % label: Interpolation order
# % description: Order for the spline/polynomial interpolation methods (ignored otherwise).
# % required: no
# % guisection: Regularization
# %end

# %option
# % key: temporal_outliers
# % type: string
# % label: Temporal-outlier filter for area 1
# % description: 'threshold,window' flags and excludes isolated, transient excursions before the analysis, tracking a running peak (or trough) and following the signal away from it, the same running-extremum approach t.rast.event uses to detect disturbance/recovery events. A descent (or ascent) is confirmed, and its entire span excluded, once it has moved at least 'threshold' away from that running reference (in the data's own units, e.g. 0.3 NDVI units) and the series is then seen to come back close to the reference again, within 'window' of leaving it (calendar days for absolute time, time steps for relative time) -- as opposed to a genuine, sustained change, which is left untouched. The removed values are dropped before STL/trend, filled in like any other gap, and still marked on the Observed panel. See the manual for the full rule.
# % required: no
# % guisection: Regularization
# %end

# %option
# % key: temporal_outliers2
# % type: string
# % label: Temporal-outlier filter for area 2
# % description: Same as 'temporal_outliers', applied to area 2.
# % required: no
# % guisection: Regularization
# %end

# %option
# % key: period
# % type: integer
# % label: Seasonal period
# % description: Number of observations per seasonal cycle (statsmodels STL 'period'). If not set, inferred from the resampled DatetimeIndex frequency.
# % required: no
# % guisection: STL
# %end

# %option
# % key: seasonal
# % type: integer
# % label: Seasonal smoother length
# % description: Length of the seasonal LOESS smoother (statsmodels STL 'seasonal'). Must be an odd integer >= 7. If not set, inferred from data.
# % required: no
# % guisection: STL
# %end

# %option
# % key: trend
# % type: integer
# % label: Trend smoother length
# % description: Length of the trend LOESS smoother (statsmodels STL 'trend'). Must be an odd integer. If not set, inferred from data.
# % required: no
# % guisection: STL
# %end

# %option
# % key: low_pass
# % type: integer
# % label: Low-pass smoother length
# % description: Length of the low-pass LOESS smoother (statsmodels STL 'low_pass'). Must be an odd integer >= 3. Defaults to the smallest odd integer > period.
# % required: no
# % guisection: STL
# %end

# %option
# % key: seasonal_degree
# % type: integer
# % label: Seasonal LOESS degree
# % description: Degree of the seasonal LOESS polynomial (statsmodels STL 'seasonal_deg'). Default is 1.
# % options: 0,1
# % answer: 1
# % required: no
# % guisection: STL
# %end

# %option
# % key: trend_degree
# % type: integer
# % label: Trend LOESS degree
# % description: Degree of the trend LOESS polynomial (statsmodels STL 'trend_deg'). Default is 1.
# % options: 0,1
# % answer: 1
# % required: no
# % guisection: STL
# %end

# %option
# % key: low_pass_degree
# % type: integer
# % label: Low-pass LOESS degree
# % description: Degree of the low-pass LOESS polynomial (statsmodels STL 'low_pass_deg'). Default is 1.
# % options: 0,1
# % answer: 1
# % required: no
# % guisection: STL
# %end

# %option
# % key: seasonal_jump
# % type: integer
# % label: Seasonal jump
# % description: Positive integer step the seasonal LOESS is evaluated at, interpolating in between (statsmodels STL 'seasonal_jump'). Higher is faster, less exact. Default is 1.
# % answer: 1
# % required: no
# % guisection: STL
# %end

# %option
# % key: trend_jump
# % type: integer
# % label: Trend jump
# % description: Positive integer step the trend LOESS is evaluated at (statsmodels STL 'trend_jump'). Default is 1.
# % answer: 1
# % required: no
# % guisection: STL
# %end

# %option
# % key: low_pass_jump
# % type: integer
# % label: Low-pass jump
# % description: Positive integer step the low-pass LOESS is evaluated at (statsmodels STL 'low_pass_jump'). Default is 1.
# % answer: 1
# % required: no
# % guisection: STL
# %end

# %flag
# % key: r
# % label: Robust STL fitting
# % description: Use robust (data-dependent) weighting in the STL fit (statsmodels STL robust=True).
# % guisection: STL
# %end

# %flag
# % key: o
# % label: OLS trend line
# % description: Add the ordinary least-squares (OLS) regression line (slope and R^2) to the trend panel.
# % guisection: Trend line
# %end

# %flag
# % key: s
# % label: Theil-Sen trend line
# % description: Add the robust Theil-Sen regression line (slope and Mann-Kendall p-value) to the trend panel.
# % guisection: Trend line
# %end

# %flag
# % key: t
# % label: Trend-line statistics in plot
# % description: Show the trend-line statistics (slope, R^2, Mann-Kendall p-value) in the plot legend. They are always printed to the terminal regardless of this flag.
# % guisection: Trend line
# %end

# %option
# % key: slope_unit
# % type: string
# % label: Reporting unit for trend slopes
# % description: Time unit the reported OLS/Theil-Sen slopes are expressed per (value change per unit). 'auto' picks a readable calendar unit (day/week/month/year) from the series span for absolute-time data; 'step' keeps the value change per observation step (per frequency/step). For relative-time data only 'auto' and 'step' apply.
# % options: auto,step,day,week,month,year
# % answer: auto
# % required: no
# % guisection: Trend line
# %end

# %option
# % key: trend_trim
# % type: string
# % label: Trend regression edge trim
# % description: How much of each end of the trend component to drop before fitting the trend regression, expressed as a fraction of the STL trend-smoother window. See below for more details.
# % options: none,0.1,0.25,0.5,1
# % answer: none
# % required: no
# % guisection: Trend line
# %end

# %option
# % key: breakpoints
# % type: string
# % label: Trend regression breakpoints
# % description: Date(s) (absolute-time strds) or time step(s) (relative-time strds) splitting the trend regression into separate segments, e.g. to report the slope before and after a known change rather than one slope that averages over it. Each value starts a new segment; the series' own start and end always count as the outer segment boundaries. Comma separated for multiple breakpoints. 'trend_trim' only trims the series' true start/end, not an interior breakpoint (which is not a LOESS edge). Combine with 'vlines' (same dates/steps) to also mark the breakpoints on the plot.
# % multiple: yes
# % required: no
# % guisection: Trend line
# %end

# %option
# % key: plots
# % type: string
# % label: Panels to include in the figure
# % description: Which decomposition panels to draw, as a comma separated subset of observed, trend, seasonal and residual. Omitted panels are left out of the figure; at least one panel is required. The trend regression lines are only drawn when the trend panel is included.
# % options: observed,trend,seasonal,residual
# % multiple: yes
# % answer: observed,trend,seasonal,residual
# % required: no
# % guisection: Plotting
# %end

# %option
# % key: style
# % type: string
# % label: Matplotlib style
# % description: Name of a built-in Matplotlib style (see https://matplotlib.org/stable/gallery/style_sheets/style_sheets_reference.html), or the path to a custom .mplstyle file (see https://matplotlib.org/stable/tutorials/introductory/customizing.html#defining-your-own-style).
# % required: no
# % guisection: Plotting
# %end

# %option
# % key: fontsize
# % type: double
# % label: Font size
# % description: Base font size of plot text. Defaults to the Matplotlib/style default.
# % required: no
# % guisection: Plotting
# %end

# %option
# % key: line_width
# % type: double
# % label: Line width
# % description: Width of the series lines. Defaults to the Matplotlib default.
# % required: no
# % guisection: Plotting
# %end

# %option
# % key: title
# % type: string
# % label: Plot title
# % description: The title of the plot. If left empty, no title is drawn.
# % required: no
# % guisection: Plotting
# %end

# %flag
# % key: d
# % label: Show pixel-value spread band
# % description: Shade a band around the Observed series showing the spread of pixel values within an area at each timestep: +/-1 standard deviation for the 'mean' statistic, or the interquartile range (25th-75th percentile) for the 'median' statistic. Only valid with 'statistic=mean' or 'statistic=median'; only drawn for whichever area(s) are defined by 'zone'/'raster'/'zone2'/'raster2' rather than a point.
# % guisection: Plotting
# %end

# %flag
# % key: e
# % label: Hide outlier markers
# % description: Do not draw the markers for values excluded by 'temporal_outliers'/'temporal_outliers2' on the Observed panel (no effect if neither option is set, or none were excluded). The Observed panel's y-axis is then left to autoscale to the plotted (gap-filled) series only, instead of being stretched to also fit the hidden outlier values.
# % guisection: Plotting
# %end

# %option
# % key: min_pixels
# % type: integer
# % label: Minimum pixel count for the spread band
# % description: At timesteps where fewer than this many non-null pixels contributed to an area's statistic, the spread band (-d) is left out and interpolated like any other gap, instead of plotting it. A standard deviation or interquartile range estimated from very few pixels is unreliable and can spike far beyond the genuine spread, most visibly on near-total-cloud timesteps where only a handful of pixels survive. Only meaningful with -d.
# % required: no
# % guisection: Plotting
# %end

# %option
# % key: seasonal_envelope
# % type: string
# % label: Seasonal amplitude envelope percentile
# % description: Draw a rolling envelope of the seasonal component (a centered window one seasonal period wide) on the Seasonal panel, showing how the seasonal amplitude changes over time. The value is the fraction trimmed from each end of the window before taking the envelope, e.g. '0.1' uses the 10th/90th percentile instead of the min/max, to avoid outliers dominating the envelope; '0' uses the plain min/max. Unset disables the envelope.
# % required: no
# % guisection: Plotting
# %end

# %option G_OPT_CN
# % key: color
# % type: string
# % label: Line color for area 1
# % description: Color of the area-1 series lines. Accepts a GRASS color name (e.g. 'blue'), an R:G:B triplet (e.g. '0:0:255'), or any matplotlib color such as a hex code ('#1f77b4') or 'tab:' name. The trend-regression lines for this area are drawn in a matching darker/lighter family. Defaults to the Matplotlib default.
# % required: no
# % answer:
# % guisection: Plotting
# %end

# %option G_OPT_CN
# % key: color2
# % type: string
# % label: Line color for area 2
# % description: Color of the area-2 series lines. Accepts a GRASS color name, an R:G:B triplet, or any matplotlib color (hex code or 'tab:' name). Its trend-regression lines use a matching family. Defaults to the Matplotlib default.
# % required: no
# % answer:
# % guisection: Plotting
# %end

# %option
# % key: vlines
# % type: string
# % label: Vertical reference line date(s)
# % description: Date(s) (absolute-time strds, e.g. '2019-08-15') or time step(s) (relative-time strds, integer) at which to draw a dashed vertical reference line across all panels, e.g. to mark a known event. Comma separated for multiple lines.
# % multiple: yes
# % required: no
# % guisection: Plotting
# %end

# %option
# % key: vlines_labels
# % type: string
# % label: Vertical reference line label(s)
# % description: Optional label(s) for the 'vlines' dates, in the same order. When given, the number of labels must match the number of 'vlines' values. Shown rotated above the top panel.
# % multiple: yes
# % required: no
# % guisection: Plotting
# %end

# %option G_OPT_F_OUTPUT
# % key: output
# % required: no
# % label: Name of output plot file
# % description: Output image file. The format is taken from the extension (e.g. .png, .pdf, .svg). If omitted, the plot is shown in an interactive window.
# % guisection: Output
# %end

# %option
# % key: backend
# % type: string
# % label: Matplotlib backend
# % description: Matplotlib rendering backend. WXAgg (default) opens an interactive window. Agg is non-interactive and used automatically when saving to a file.
# % options: WXAgg,TkAgg,Qt5Agg,GTK3Agg,Agg
# % required: no
# % guisection: Output
# %end

# %option
# % key: dpi
# % type: integer
# % label: DPI
# % description: Plot resolution in DPI.
# % answer: 300
# % required: no
# % guisection: Output
# %end

# %option
# % key: plot_dimensions
# % type: string
# % label: Plot dimensions (width,height)
# % description: Dimensions (width,height) of the figure in inches.
# % required: no
# % guisection: Output
# %end

# %option G_OPT_M_NPROCS
# % description: Number of parallel processes. For a point ('coordinates'/'coordinates2') this has no effect. For an area ('zone'/'raster'/'zone2'/'raster2') it is forwarded to t.rast.univar's zonal extraction.
# %end

# %option G_OPT_T_WHERE
# %end

# %rules
# % exclusive: coordinates, zone, raster
# % required: coordinates, zone, raster
# % exclusive: coordinates2, zone2, raster2
# % required: coordinates2, zone2, raster2
# % requires: -d, zone, raster, zone2, raster2
# % requires: min_pixels, -d
# % requires: vlines_labels, vlines
# %end


import atexit
import sys

import grass.script as gs
from grass.exceptions import CalledModuleError
from grass.script.utils import set_path

if not callable(globals().get("_")):
    from gettext import gettext as _

# extract.py/trend.py/plot.py: this module's own library files (see the
# ETCFILES entry in the Makefile), originally split out of t.rast.stl --
# this addon keeps its own copy since each GRASS addon is installed
# independently. set_path() finds them whether this script is run from its
# installed location or straight from the source tree. Each library file
# leaves its own numpy/pandas/matplotlib/statsmodels/scipy names as None at
# import time (set below, by lazy_import_py_modules(), once GRASS has
# parsed the command line) so a plain module scan (--help, g.extension)
# never needs the scientific stack installed.
set_path("t.rast.stl2ca")
import extract  # noqa: E402
import trend  # noqa: E402
import plot  # noqa: E402
from extract import (  # noqa: E402
    clean_dirs,
    clean_rasters,
    coords_from_option,
    validate_zone,
    make_zone_raster,
    zone_bbox_center,
    validate_raster,
    make_raster_zone,
    raster_bbox_center,
    extract_series,
    extract_zonal_series,
    build_series,
    parse_temporal_outliers,
    detect_temporal_outliers,
    regularize,
)
from trend import decompose_and_fit, validate_odd_window  # noqa: E402
from plot import apply_style, grass_color_to_mpl, plot_result, parse_vlines  # noqa: E402


def cleanup():
    """Remove temporary directories and rasters registered during the run."""
    for path in clean_dirs:
        gs.try_rmdir(path)
    if clean_rasters:
        gs.run_command(
            "g.remove", flags="f", type="raster", name=clean_rasters, quiet=True
        )


def lazy_import_py_modules(backend="WXAgg"):
    """Lazy import of the third-party scientific stack.

    Imports numpy/pandas/statsmodels/scipy/matplotlib once the command line
    has been parsed, and hands each to the library module(s) that use it --
    extract.py/trend.py/plot.py each leave the name as None at import time
    (see their module docstrings) until this runs. This is what keeps a
    plain module scan (--help, g.extension) from ever needing the
    scientific stack installed, now that it lives across four files instead
    of one.

    :param str backend: matplotlib backend to activate before importing pyplot
    """
    try:
        import numpy as np
        import pandas as pd
    except ModuleNotFoundError as e:
        gs.fatal(
            _(
                "The Python package '{pkg}' is required but not installed. "
                "Install it with e.g. 'pip install numpy pandas'."
            ).format(pkg=e.name)
        )

    try:
        from statsmodels.tsa.seasonal import STL
    except ModuleNotFoundError:
        gs.fatal(
            _(
                "The Python package 'statsmodels' is required for the STL "
                "decomposition but is not installed. Install it with e.g. "
                "'pip install statsmodels'."
            )
        )

    try:
        from scipy.stats import kendalltau, linregress, theilslopes
    except ModuleNotFoundError:
        gs.fatal(
            _(
                "The Python package 'scipy' is required for the trend "
                "regression but is not installed. Install it with e.g. "
                "'pip install scipy'."
            )
        )

    try:
        import matplotlib as mpl

        mpl.use(backend)
        from matplotlib import pyplot as plt
    except ModuleNotFoundError:
        gs.fatal(_("Matplotlib is required but not installed. Please install it."))

    extract.np = np
    extract.pd = pd
    trend.np = np
    trend.pd = pd
    trend.STL = STL
    trend.linregress = linregress
    trend.theilslopes = theilslopes
    trend.kendalltau = kendalltau
    plot.np = np
    plot.pd = pd
    plot.mpl = mpl
    plot.plt = plt


def validate_options(options, flags, temporal_type):
    """Validate option values that depend only on user input (and the cheap
    t.info temporal type), so the module fails fast before the potentially
    expensive t.rast.what/t.rast.univar sampling step.

    Checks performed here:
      * seasonal / trend / low_pass are odd integers >= their minimum
      * the *_jump options are positive integers
      * spline / polynomial interpolation requires 'order'
      * a relative-time 'step' override is a positive integer
      * an absolute-time 'frequency' is a valid pandas offset alias
      * temporal_outliers/temporal_outliers2 parse as 'threshold,window'
      * statistic=percentile requires percentile_value
      * the -d (dispersion band) flag only applies to statistic=mean/median
      * min_pixels, when given, is a positive integer

    Data-dependent checks (period vs. length, gaps after interpolation, etc.)
    are intentionally left to run later, once the series is available.

    :param dict options: parsed module options
    :param dict flags: parsed module flags
    :param str temporal_type: 'absolute' or 'relative' (from t.info)
    """
    # statistic=percentile needs an explicit percentile_value; the dispersion
    # band (-d) has no natural paired spread value outside mean/median, so it
    # is restricted to those two statistics rather than silently showing a
    # misleading band.
    statistic = options["statistic"]
    if statistic == "percentile" and not options["percentile_value"]:
        gs.fatal(
            _("The 'percentile_value' option is required when 'statistic' is 'percentile'.")
        )
    if flags["d"] and statistic not in ("mean", "median"):
        gs.fatal(
            _(
                "The '-d' flag (pixel-value spread band) is only meaningful "
                "with 'statistic=mean' or 'statistic=median'."
            )
        )
    if options["min_pixels"] and int(options["min_pixels"]) < 1:
        gs.fatal(_("The 'min_pixels' option must be a positive integer."))

    # STL LOESS window lengths: odd integers, each with its own minimum.
    validate_odd_window(options["seasonal"], "seasonal", 7)
    validate_odd_window(options["trend"], "trend", 3)
    validate_odd_window(options["low_pass"], "low_pass", 3)

    # LOESS jump steps must be positive integers.
    for key in ("seasonal_jump", "trend_jump", "low_pass_jump"):
        if options[key] and int(options[key]) < 1:
            gs.fatal(_("'{}' must be a positive integer.").format(key))

    # Spline/polynomial interpolation needs an explicit order.
    if options["interpolation"] in ("spline", "polynomial") and not options["order"]:
        gs.fatal(
            _("The '{}' interpolation method requires the 'order' option.").format(
                options["interpolation"]
            )
        )

    # At least one panel must be kept in the figure.
    if not [p for p in options["plots"].split(",") if p]:
        gs.fatal(
            _(
                "At least one panel must be selected in the 'plots' option "
                "(observed, trend, seasonal and/or residual)."
            )
        )

    # Relative-time step override, when given, must be a positive integer.
    if temporal_type == "relative" and options["step"]:
        if int(options["step"]) <= 0:
            gs.fatal(_("The 'step' option must be a positive integer."))

    # Absolute-time 'frequency', when given, must be a pandas offset alias
    # (a unit, optionally with a multiplier), e.g. 'D', 'W', 'MS', '16D',
    # '5YS'. A bare number has no unit and pandas rejects it with an opaque
    # message. The below will catch it and give a clear message instead.
    if temporal_type == "absolute" and options["frequency"]:
        try:
            # lazy_import_py_modules() (called before this) has already set
            # extract.pd; validate_options() itself has no reason to import
            # pandas again just for this one check.
            extract.pd.tseries.frequencies.to_offset(options["frequency"])
        except (ValueError, TypeError):
            gs.fatal(
                _(
                    "The 'frequency' value '{v}' is not a valid pandas offset "
                    "alias. It needs a time unit, optionally with a leading "
                    "multiplier, e.g. 'D' (day), 'W' (week), 'MS' (month "
                    "start), '16D' (16 days), 'YS' or '5YS' (year start). A "
                    "bare number is not accepted."
                ).format(v=options["frequency"])
            )

    # temporal_outliers / temporal_outliers2, when given, must parse as
    # 'threshold,window'.
    parse_temporal_outliers(options["temporal_outliers"], "temporal_outliers")
    parse_temporal_outliers(options["temporal_outliers2"], "temporal_outliers2")

    # Line colours, when given, must be valid GRASS colour specs that map to a
    # colour matplotlib understands (a named colour or an R:G:B[:A] triplet).
    import matplotlib.colors as _mcolors

    for key in ("color", "color2"):
        if options.get(key):
            try:
                converted = grass_color_to_mpl(options[key])
                # None means 'none' (no explicit colour) -> acceptable.
                ok = converted is None or _mcolors.is_color_like(converted)
            except ValueError:
                ok = False
            if not ok:
                gs.fatal(
                    _(
                        "'{k}' value '{v}' is not a valid colour. Use a GRASS "
                        "colour name (e.g. 'blue'), an R:G:B triplet with each "
                        "component in 0-255 (e.g. '0:0:255'), or any matplotlib "
                        "colour such as a hex code ('#1f77b4') or 'tab:' name."
                    ).format(k=key, v=options[key])
                )


def resolve_area(options, suffix, statistic):
    """Resolve one area= option group into a sampling area.

    Mirrors t.rast.stl's single area lookup (point, or a zone rasterized
    from a vector map, or a zone taken from a raster's non-null cells); here
    it is called twice, once per area, with ``suffix`` selecting which
    option group to read ('' for area 1, '2' for area 2).

    :param dict options: parsed module options
    :param str suffix: '' for area 1, '2' for area 2
    :param str statistic: the statistic= option value, for the terminal message
    :return tuple: (zone_raster_or_None, east, north, label) where label is
        the zone/raster map name (mapset stripped) or the point coordinates,
        used in terminal messages and as the plot legend entry
    """
    coordinates = options["coordinates" + suffix]
    zone = options["zone" + suffix]
    raster = options["raster" + suffix]

    if zone:
        validate_zone(zone)
        zone_raster = make_zone_raster(zone)
        east, north = zone_bbox_center(zone)
        label = zone.split("@")[0]
        gs.message(
            _(
                "Using zone '{}' ({} statistic; bbox center for tagging: "
                "east={}, north={})."
            ).format(zone, statistic, east, north)
        )
    elif raster:
        validate_raster(raster)
        zone_raster = make_raster_zone(raster)
        east, north = raster_bbox_center(raster)
        label = raster.split("@")[0]
        gs.message(
            _(
                "Using raster '{}' non-null cells ({} statistic; bbox center "
                "for tagging: east={}, north={})."
            ).format(raster, statistic, east, north)
        )
    else:
        east, north = coords_from_option(coordinates)
        zone_raster = None
        label = "{},{}".format(east, north)
        gs.message(_("Using point (east, north) = ({}, {})").format(east, north))

    return zone_raster, east, north, label


def main(options, flags):
    """Extract two area series from one strds and compare their STL decompositions."""

    output = options["output"]
    backend_opt = options["backend"]
    statistic = options["statistic"]
    percentile_value = float(options["percentile_value"]) if options["percentile_value"] else None
    strds = options["strds"]
    where = options["where"]
    nprocs = int(options["nprocs"]) if options["nprocs"] else 1
    frequency = options["frequency"]
    interpolation = options["interpolation"]
    order = options["order"]
    step = options["step"]
    period_opt = options["period"]
    seasonal = options["seasonal"]
    trend = options["trend"]
    low_pass = options["low_pass"]
    seasonal_degree = options["seasonal_degree"]
    trend_degree = options["trend_degree"]
    low_pass_degree = options["low_pass_degree"]
    seasonal_jump = options["seasonal_jump"]
    trend_jump = options["trend_jump"]
    low_pass_jump = options["low_pass_jump"]
    trend_trim = options["trend_trim"]
    breakpoints_opt = options["breakpoints"]
    slope_unit = options["slope_unit"]
    plot_dimensions = options["plot_dimensions"]
    plots = [p for p in options["plots"].split(",") if p] if options["plots"] else []
    dpi = float(options["dpi"]) if options["dpi"] else 300
    envelope_percentile = None
    if options["seasonal_envelope"]:
        envelope_percentile = float(options["seasonal_envelope"])
        if not 0 <= envelope_percentile < 0.5:
            gs.fatal(_("The 'seasonal_envelope' option must be >= 0 and < 0.5."))

    robust = flags["r"]
    show_ols = flags["o"]
    show_sen = flags["s"]
    show_stats = flags["t"]
    show_dispersion = flags["d"]
    hide_outliers = flags["e"]
    min_pixels = int(options["min_pixels"]) if options["min_pixels"] else None
    line_color = grass_color_to_mpl(options["color"]) if options["color"] else None
    line_color2 = grass_color_to_mpl(options["color2"]) if options["color2"] else None
    fontsize = float(options["fontsize"]) if options["fontsize"] else None
    line_width = float(options["line_width"]) if options["line_width"] else None
    title = options["title"]

    # Select the matplotlib backend: explicit > output-driven default.
    if backend_opt:
        backend = backend_opt
    elif output:
        backend = "Agg"
    else:
        backend = "WXAgg"
    lazy_import_py_modules(backend=backend)
    apply_style(options["style"])

    # A nudge, not a fatal error: the two areas are allowed to be the same
    # (e.g. while testing), but the resulting comparison is trivial.
    if (
        (options["coordinates"] and options["coordinates"] == options["coordinates2"])
        or (options["zone"] and options["zone"] == options["zone2"])
        or (options["raster"] and options["raster"] == options["raster2"])
    ):
        gs.warning(_("Area 1 and area 2 are the same; the comparison will be trivial."))

    # Resolve the two sampling areas: each is either a point, a zone
    # rasterized from a vector map, or a zone taken from a raster's non-null
    # cells (all pooled into a single sample).
    area1 = resolve_area(options, "", statistic)
    area2 = resolve_area(options, "2", statistic)

    # Check if the strds exists and read its temporal type.
    try:
        tinfo = gs.parse_command("t.info", flags="g", input=strds)
    except CalledModuleError:
        gs.fatal(_("Space-time raster dataset '{}' not found.").format(strds))
    temporal_type = tinfo.get("temporal_type", "absolute")

    # Validate option-only requirements up front.
    validate_options(options, flags, temporal_type)

    # Vertical reference lines (dates for absolute time, time steps for
    # relative time), parsed here (after the temporal type is known) so a bad
    # value is caught before the expensive sampling step below.
    vlines = parse_vlines(options["vlines"], options["vlines_labels"], temporal_type)

    stl_kwargs = {
        "seasonal": seasonal,
        "trend": trend,
        "low_pass": low_pass,
        "seasonal_deg": seasonal_degree,
        "trend_deg": trend_degree,
        "low_pass_deg": low_pass_degree,
        "seasonal_jump": seasonal_jump,
        "trend_jump": trend_jump,
        "low_pass_jump": low_pass_jump,
        "robust": robust,
    }

    # Extract -> regularize -> decompose/fit each area. The terminal messages
    # for each are prefixed with its label so the two analyses can be told
    # apart.
    outliers_keys = ("temporal_outliers", "temporal_outliers2")
    results = []
    bands = []
    envelopes = []
    excluded_points = []
    for index, (zone_raster, east, north, label) in enumerate((area1, area2)):
        if zone_raster:
            gs.message(_("Extracting the zonal time series for '{}'...").format(label))
            ds_dates, ds_values, ds_lower, ds_upper, ds_pixel_counts = extract_zonal_series(
                strds=strds,
                zone_raster=zone_raster,
                where=where,
                statistic=statistic,
                nprocs=nprocs,
                want_dispersion=show_dispersion,
                percentile_value=percentile_value,
            )
        else:
            gs.message(_("Extracting the point time series for '{}'...").format(label))
            ds_dates, ds_values = extract_series(
                strds=strds,
                east=east,
                north=north,
                where=where,
                nprocs=nprocs,
            )
            ds_lower = ds_upper = ds_pixel_counts = None

        ds_series = build_series(ds_dates, ds_values, temporal_type=temporal_type)
        n_valid = int(ds_series.notna().sum())
        gs.message(
            _("Extracted {n} timesteps ({v} non-null).").format(
                n=len(ds_series), v=n_valid
            )
        )
        if n_valid == 0:
            gs.fatal(
                _(
                    "All extracted values are NULL for '{}'; nothing to "
                    "decompose."
                ).format(label)
            )

        outliers_key = outliers_keys[index]
        ds_outliers = parse_temporal_outliers(options[outliers_key], outliers_key)
        if ds_outliers is not None:
            ds_threshold, ds_window = ds_outliers
            ds_series, ds_excluded = detect_temporal_outliers(
                ds_series, ds_threshold, ds_window, temporal_type=temporal_type
            )
        else:
            ds_excluded = ds_series.iloc[0:0]
        if len(ds_excluded):
            gs.message(
                _(
                    "Flagged {n} value(s) in '{d}' as transient temporal "
                    "outliers (threshold={t}, window={w}); linearly "
                    "interpolated."
                ).format(n=len(ds_excluded), d=label, t=ds_threshold, w=ds_window)
            )
            # Fill just these dates with linear interpolation now, ahead of
            # the 'interpolation' method below. An excursion can span many
            # steps (up to 'window'), and a curvature-fitting method
            # (quadratic, cubic, spline...) bridging a gap that wide can
            # overshoot past either neighbour, undoing the whole point of
            # excluding the outlier by replacing it with a different,
            # possibly larger artifact. Linear is bounded by its two
            # neighbours and cannot do that. Genuine gaps (still NaN here)
            # are left for the chosen 'interpolation' method, unchanged.
            linear_filled = ds_series.interpolate(
                method="linear", limit_direction="both"
            )
            ds_series.loc[ds_excluded.index] = linear_filled.loc[ds_excluded.index]
        excluded_points.append(ds_excluded)

        gs.message(_("Regularizing the series and interpolating gaps..."))
        ds_regular = regularize(
            series=ds_series,
            frequency=frequency,
            method=interpolation,
            order=order,
            temporal_type=temporal_type,
            step=step,
            tinfo=tinfo,
        )

        # The dispersion band (if any) is observed-panel annotation only; it
        # is regularized onto the same grid as the series but never goes
        # through decompose_and_fit()/STL.
        ds_band_lower = ds_band_upper = None
        if ds_lower is not None:
            ds_lower_series = build_series(ds_dates, ds_lower, temporal_type=temporal_type)
            ds_upper_series = build_series(ds_dates, ds_upper, temporal_type=temporal_type)
            if len(ds_excluded):
                # Blank the band at the same dates excluded from the main
                # series, so it is interpolated through them too instead of
                # still showing the raw (possibly contaminated) pixel spread
                # at a timestep the series itself no longer shows as data.
                excluded_dates = ds_lower_series.index.isin(ds_excluded.index)
                ds_lower_series = ds_lower_series.mask(excluded_dates)
                ds_upper_series = ds_upper_series.mask(excluded_dates)
            if min_pixels is not None and ds_pixel_counts is not None:
                # A spread computed from very few pixels is a poor estimate
                # and can spike far past the genuine spread -- typically a
                # near-total-cloud timestep where only a handful of pixels
                # survive -- even though the mean/median itself (and so
                # temporal_outliers, which only watches that) looks normal.
                ds_count_series = build_series(
                    ds_dates, ds_pixel_counts, temporal_type=temporal_type
                )
                low_count_dates = ds_count_series < min_pixels
                n_low_count = int(low_count_dates.sum())
                if n_low_count:
                    gs.message(
                        _(
                            "Spread band left out at {n} timestep(s) in '{d}' "
                            "with fewer than {m} non-null pixels."
                        ).format(n=n_low_count, d=label, m=min_pixels)
                    )
                    ds_lower_series = ds_lower_series.mask(low_count_dates)
                    ds_upper_series = ds_upper_series.mask(low_count_dates)
            # Always interpolated linearly, regardless of 'interpolation': a
            # curvature-fitting method (quadratic, cubic, spline...) can
            # overshoot past either neighbour when bridging a gap, which for
            # a dispersion band means manufacturing a bulge wider than the
            # genuine spread on either side -- most visibly across the
            # multi-step spans temporal_outliers excludes. Linear is bounded
            # by its two neighbours and cannot do that.
            ds_band_lower = regularize(
                series=ds_lower_series,
                frequency=frequency,
                method="linear",
                order=None,
                temporal_type=temporal_type,
                step=step,
                tinfo=tinfo,
                report=False,
            )
            ds_band_upper = regularize(
                series=ds_upper_series,
                frequency=frequency,
                method="linear",
                order=None,
                temporal_type=temporal_type,
                step=step,
                tinfo=tinfo,
                report=False,
            )
        bands.append((ds_band_lower, ds_band_upper))

        (
            ds_result,
            ds_trend_fit,
            ds_trend_fit_segments,
            ds_envelope_lower,
            ds_envelope_upper,
        ) = decompose_and_fit(
            ds_regular,
            period_opt,
            temporal_type,
            tinfo,
            stl_kwargs,
            trend_trim,
            show_ols,
            show_sen,
            False,  # show_gam: not exposed in this addon's interface
            None,  # gam_direction: unused when show_gam is False
            frequency=frequency,
            step=step,
            slope_unit=slope_unit,
            label=label,
            envelope_percentile=envelope_percentile,
            breakpoints_opt=breakpoints_opt,
        )
        results.append((ds_result, ds_trend_fit, ds_trend_fit_segments))
        envelopes.append((ds_envelope_lower, ds_envelope_upper))

    result, trend_fit, trend_fit_segments = results[0]
    result2, trend_fit2, trend_fit_segments2 = results[1]
    band_lower, band_upper = bands[0]
    band_lower2, band_upper2 = bands[1]
    band_label = None
    if show_dispersion:
        band_label = _("± 1 SD") if statistic == "mean" else _("IQR (25-75%)")
    envelope_lower, envelope_upper = envelopes[0]
    envelope_lower2, envelope_upper2 = envelopes[1]
    if hide_outliers:
        excluded = excluded2 = None
    else:
        excluded = excluded_points[0]
        excluded2 = excluded_points[1]

    # Plot (save-by-extension or show).
    gs.message(_("Creating the figure..."))
    if plot_dimensions:
        dimensions = [float(x) for x in plot_dimensions.split(",")]
    else:
        # Default height scales with the number of panels (2 inches each), so
        # the full four-panel figure stays 8x8 while smaller selections are not
        # stretched vertically.
        dimensions = [8, 2 * len(plots)]
    plot_result(
        result=result,
        output=output,
        dpi=dpi,
        dimensions=dimensions,
        east=area1[1],
        north=area1[2],
        temporal_type=temporal_type,
        trend_fit=trend_fit,
        trend_fit_segments=trend_fit_segments,
        show_ols=show_ols,
        show_sen=show_sen,
        show_gam=False,
        show_band=False,
        show_stats=show_stats,
        result2=result2,
        trend_fit2=trend_fit2,
        trend_fit_segments2=trend_fit_segments2,
        strds_name=area1[3],
        strds2_name=area2[3],
        same_yscale=True,
        line_color=line_color,
        line_color2=line_color2,
        fontsize=fontsize,
        line_width=line_width,
        title=title,
        plots=plots,
        band_lower=band_lower,
        band_upper=band_upper,
        band_lower2=band_lower2,
        band_upper2=band_upper2,
        band_label=band_label,
        envelope_lower=envelope_lower,
        envelope_upper=envelope_upper,
        envelope_lower2=envelope_lower2,
        envelope_upper2=envelope_upper2,
        excluded=excluded,
        excluded2=excluded2,
        vlines=vlines,
    )


if __name__ == "__main__":
    atexit.register(cleanup)
    sys.exit(main(*gs.parser()))
