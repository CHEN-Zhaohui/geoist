"""
Gridding with splines
=====================

Biharmonic spline interpolation is based on estimating vertical forces acting on an
elastic sheet that yield deformations in the sheet equal to the observed data. The
results are similar to using :class:`verde.ScipyGridder` with ``method='cubic'`` but
the interpolation is usually a bit slower. However, the advantage of using
:class:`verde.Spline` is that we can assign weights to the data and do model selection.
"""
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import pyproj
import numpy as np
import geoist.gridder.blockreduce as gg
from geoist.others import fetch_data
import geoist.gridder.coordinates as cd
from geoist.gridder import chain, spline, model_selection, mask

# We'll test this on the air temperature data from Texas
data = fetch_data.fetch_texas_wind()
coordinates = (data.longitude.values, data.latitude.values)
region = cd.get_region(coordinates)

# Use a Mercator projection for our Cartesian gridder
projection = pyproj.Proj(proj="merc", lat_ts=data.latitude.mean())

# The output grid spacing will 15 arc-minutes
spacing = 15 / 60

# Now we can chain a blocked mean and spline together. The Spline can be regularized
# by setting the damping coefficient (should be positive). It's also a good idea to set
# the minimum distance to the average data spacing to avoid singularities in the spline.
chain = chain.Chain(
    [
        ("mean", gg.BlockReduce(np.mean, spacing=spacing * 111e3)),
        ("spline", spline.Spline(damping=1e-10, mindist=100e3)),
    ]
)
print(chain)

# We can evaluate model performance by splitting the data into a training and testing
# set. We'll use the training set to grid the data and the testing set to validate our
# spline model.
train, test = model_selection.train_test_split(
    projection(*coordinates), data.air_temperature_c, random_state=0
)

# Fit the model on the training set
chain.fit(*train)

# And calculate an R^2 score coefficient on the testing set. The best possible score
# (perfect prediction) is 1. This can tell us how good our spline is at predicting data
# that was not in the input dataset.
score = chain.score(*test)
print("\nScore: {:.3f}".format(score))

# Now we can create a geographic grid of air temperature by providing a projection
# function to the grid method and mask points that are too far from the observations
grid_full = chain.grid(
    region=region,
    spacing=spacing,
    projection=projection,
    dims=["latitude", "longitude"],
    data_names=["temperature"],
)
grid = mask.distance_mask(
    coordinates, maxdist=3 * spacing * 111e3, grid=grid_full, projection=projection
)
print(grid)

# Plot the grid and the original data points
plt.figure(figsize=(8, 6))
ax = plt.axes(projection=ccrs.Mercator())
ax.set_title("Air temperature gridded with biharmonic spline")
ax.plot(*coordinates, ".k", markersize=1, transform=ccrs.PlateCarree())
tmp = grid.temperature.plot.pcolormesh(
    ax=ax, cmap="plasma", transform=ccrs.PlateCarree(), add_colorbar=False
)
plt.colorbar(tmp).set_label("Air temperature (C)")
# Use an utility function to add tick labels and land and ocean features to the map.
fetch_data.setup_texas_wind_map(ax, region=region)
plt.tight_layout()
plt.show()
