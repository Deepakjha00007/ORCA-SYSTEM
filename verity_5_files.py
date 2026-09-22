import os
import glob
import xarray as xr

data_dir = "data/satellite_raw"
nc_files = glob.glob(os.path.join(data_dir, "*.nc"))

print(f"Found {len(nc_files)} / 5 NetCDF dataset(s):\n" + "="*50)

for fpath in nc_files:
    fname = os.path.basename(fpath)
    print(f"\n📂 Dataset: {fname}")
    try:
        ds = xr.open_dataset(fpath)
        print(f"   - Variables: {list(ds.data_vars.keys())}")
        print(f"   - Coordinates: {list(ds.coords.keys())}")
    except Exception as e:
        print(f"   ❌ Read Error: {e}")

print("\n" + "="*50)