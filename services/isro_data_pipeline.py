import os
import requests

class ISROMosdacPipeline:
    def __init__(self):
        self.mosdac_api_url = "https://www.mosdac.gov.in/api/v1/catalog"
        self.download_dir = os.path.join(os.path.dirname(__file__), "..", "data")

    def fetch_latest_oceansat_granule(self, product_name: str = "OCEANSAT-3_OISST"):
        """
        Polls MOSDAC catalog API for new Oceansat-3 satellite passes.
        """
        api_token = os.getenv("MOSDAC_API_TOKEN", "")
        headers = {"Authorization": f"Bearer {api_token}"}
        
        try:
            response = requests.get(f"{self.mosdac_api_url}/{product_name}", headers=headers, timeout=5)
            if response.status_code == 200:
                meta = response.json()
                print(f"[MOSDAC Sync] Successfully retrieved metadata for {product_name}")
                return meta
        except Exception as e:
            print(f"[MOSDAC Pipeline] Connection skipped: {e}. Using cached NetCDF files.")
            return {"status": "OFFLINE_CACHE", "local_files": ["Oceansat-3.nc", "OISST_DATASET.nc"]}