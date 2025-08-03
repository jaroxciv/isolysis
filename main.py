from loguru import logger
from isolysis.io import IsoRequest, Centroid, Coordinate
import json

# Add file logging (diagnostics)
logger.add("out.log", backtrace=True, diagnose=True)

if __name__ == "__main__":
    req = IsoRequest(
        coordinates=[
            Coordinate(id="a", lat=13.7, lon=-89.2),
            Coordinate(id="b", lat=13.72, lon=-89.19),
        ],
        centroids=[
            Centroid(id="hub1", lat=13.7, lon=-89.2, rho=2.5),
            Centroid(id="hub2", lat=13.71, lon=-89.21, rho=3),
        ]
    )
    logger.info("IsoRequest input:\n{}", json.dumps(req.model_dump(), indent=2))
