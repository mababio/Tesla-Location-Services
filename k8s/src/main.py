import math
import teslapy
import os
import requests
import json
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from logs import Logger
from pydantic import BaseModel

"""
   wrapper around the TeslaPy Python module that returns car's location in lat,lon format
   :param request: internal gcp Function param
   :return: location if available
"""

app = FastAPI()
logger = Logger(__name__)

try:
    LAT_HOME = float(os.environ["LAT_HOME"])
    LON_HOME = float(os.environ["LON_HOME"])
    HOME_RADIUS = float(os.environ["HOME_RADIUS"])
    TESLA_USERNAME = os.environ["TESLA_USERNAME"]
    HOME_STREET = os.environ["HOME_STREET"]
    GEOAPIFY_KEY = os.environ["GEOAPIFY_KEY"]
    GEOAPIFY_URL = os.environ["GEOAPIFY_URL"]
    TESLA_DATA_SERVICES_BASE_URL = os.environ['TESLA_DATA_SERVICES_BASE_URL']
except KeyError as e:
    logger.error(str(e))
    raise

app.add_middleware(
    CORSMiddleware,
    # allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Gps(BaseModel):
    lat: float
    lon: float


def save_gps(gps):
    try:
        requests.put(f"{TESLA_DATA_SERVICES_BASE_URL}/api/car/update/gps", json=gps)
        logger.info("Attempting to save lat lon to mongodb ")
    except Exception as ef:
        logger.error(str(ef))


@app.post('/save_location')
async def save_location(gps: Gps, background_tasks: BackgroundTasks):
    background_tasks.add_task(save_gps, gps)
    return {"message": "GPS coordinate sent in the background"}


@app.get('/')
async def default(request: Request):
    if 'method' in await request.json():
        request_json = await request.json()
        match request_json['method']:
            case 'get_location':
                return get_location()
            case 'get_proximity':
                return get_proximity()
            case _:
                return {}


# TODO: In the event that person has multiple cars, we can add param to select Car. It can be on vin, display name.

@app.get('/get_location')
def get_location():
    with teslapy.Tesla(TESLA_USERNAME) as tesla:
        wanted_key = 'drive_state'
        vehicles = tesla.vehicle_list()
        timeout = 10
        try:
            vehicles[0].sync_wake_up(timeout)
            tesla_data = vehicles[0].api('VEHICLE_DATA', endpoints='location_data;')
        except teslapy.VehicleError as f:
            logger.error(f"Timeout of {timeout} second for car to wake was reached:{f}")
            raise teslapy.VehicleError

        try:
            lat = tesla_data['response'][wanted_key]['latitude']
            lon = tesla_data['response'][wanted_key]['longitude']
            speed = tesla_data['response'][wanted_key]['speed']
            return {'lat': lat, 'lon': lon, 'speed': speed}
        except KeyError as ee:
            logger.error(
                f"Keep in mind that we are using an external python Module to get tesla data. Their API may have "
                f"changed. {ee}")
            raise KeyError(f"KeyError: {ee}")


@app.get('/get_proximity')
def get_proximity():
    try:
        latlon = get_location()
        lat = float(latlon['lat'])
        lon = float(latlon['lon'])
    except Exception as eee:
        logger.error(f'Issue getting location: {eee}')
        raise KeyError('Issue with getting Car location')
    radius = 6371
    d_lat = math.radians(lat - LAT_HOME)
    d_lon = math.radians(lon - LON_HOME)
    a = math.sin(d_lat / 2) * math.sin(d_lat / 2) + math.cos(
        math.radians(LAT_HOME)) * math.cos(math.radians(lat)) * \
        math.sin(d_lon / 2) * math.sin(d_lon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    difference = radius * c
    str_difference = float(difference)
    data = {'difference': str_difference}

    if difference < HOME_RADIUS \
            or math.isclose(difference, HOME_RADIUS):
        data['is_close'] = True
        if is_on_home_street():
            # if is_on_home_street(lat, lon):
            data['is_on_arcuri'] = True
        else:
            data['is_on_arcuri'] = False

        return data
    else:
        data['is_close'] = False
        data['is_on_arcuri'] = False
        return data


@app.get('/is_home_street')
def is_on_home_street():
    try:
        car_gps = get_location()
    except Exception as ex:
        logger.error(f'Issue getting Car location {ex}')
        raise Exception

    if not isinstance(car_gps, dict) or 'lat' not in car_gps or 'lon' not in car_gps:
        logger.error("Expected location data not actual data")
        raise Exception
    else:
        try:
            gps_only = dict(list(car_gps.items())[:2])
            street = \
                requests.get(f'{GEOAPIFY_URL}?apiKey={GEOAPIFY_KEY}', params=gps_only).json()['features'][0][
                    'properties'][
                    'street']
            return json.dumps(True) if street == HOME_STREET else json.dumps(False)
        except KeyError as exc:
            logger.error(f"Issue with API: {exc}")
            raise KeyError(f"Error with Geccoding API: {exc}")


if __name__ == '__main__':
    print(get_location())
    print(get_proximity())
    print(is_on_home_street())
