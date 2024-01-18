import json
import math
import os

import requests
import teslapy
from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from logs import Logger

"""
   wrapper around the TeslaPy Python module that returns 
   car's location in lat,lon format
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


@app.get('/get_location')
async def get_location(background_tasks: BackgroundTasks):
    """
    Get location of car from Tesla API. Also save  gps to mongodb
    via Vehicle Data Services as a background task
    :param background_tasks:
    :return:
    """
    with teslapy.Tesla(TESLA_USERNAME) as tesla:
        wanted_key = 'drive_state'
        vehicles = tesla.vehicle_list()
        timeout = 10
        try:
            vehicles[0].sync_wake_up(timeout)
            logger.info(f"Getting {wanted_key} from Tesla API")
            tesla_data = vehicles[0].api('VEHICLE_DATA', endpoints='location_data;')
            logger.info(f"Got {wanted_key} from Tesla API")
        except teslapy.VehicleError as f:
            logger.error(f"Timeout of {timeout} second(s) for car to wake was reached:{f}")
            raise teslapy.VehicleError

        try:
            logger.info(f"Attempting to pull latitude, longitude and speed from "
                        f"{wanted_key}")
            lat = tesla_data['response'][wanted_key]['latitude']
            lon = tesla_data['response'][wanted_key]['longitude']
            speed = tesla_data['response'][wanted_key]['speed']
            logger.info(f"Got latitude, longitude and speed from {wanted_key}")
            logger.info(f"Attempting to save lat lon to mongodb via Vehicle Data "
                        f"Services as a background task")
            background_tasks.add_task(save_gps, {'lat': lat, 'lon': lon},
                                      vin=tesla_data['response']['vin'])
            return {'lat': lat, 'lon': lon, 'speed': speed}
        except KeyError as ee:
            logger.error(
                f"Keep in mind that we are using an external python Module "
                f"to get tesla data. Their API may have "
                f"changed. {ee}")
            raise KeyError(f"KeyError: {ee}")


# TODO: In the event that person has multiple cars,
#   we can add param to select Car. It can be on vin, display name.

@app.get('/get_proximity')
async def get_proximity(background_tasks: BackgroundTasks):
    """
    Get proximity of car using location as input. Also save gps to mongodb via
    Vehicle Data Services as a background task as a byproduct of get_location
    :param background_tasks:
    :return:
    """
    try:
        logger.info("Attempting to get location from get_location function")
        latlon = await get_location(background_tasks)
        lat = float(latlon['lat'])
        lon = float(latlon['lon'])
        logger.info("Got location from get_location function")
    except Exception as eee:
        logger.error(f'Issue getting location: {eee}')
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
        if await is_on_home_street(background_tasks):
            # if is_on_home_street(lat, lon):
            data['is_on_arcuri'] = True
        else:
            data['is_on_arcuri'] = False

        return data

    data['is_close'] = False
    data['is_on_arcuri'] = False
    return data


@app.get('/is_home_street')
async def is_on_home_street(background_tasks: BackgroundTasks):
    """
    Determine if car is on home street. Also save gps to mongodb via Vehicle
     Data Services as a background task as a byproduct of get_location
    :param background_tasks:
    :return:
    """
    try:
        logger.info("Attempting to get location from get_location function")
        car_gps = await get_location(background_tasks)
        logger.info("Got location from get_location function")
    except Exception as ex:
        logger.error(f'Issue getting Car location {ex}')
        raise Exception(f'Issue getting Car location {ex}')

    if not isinstance(car_gps, dict) or 'lat' not in car_gps or 'lon' not in car_gps:
        logger.error("Expected location data not actual data")
        raise Exception("Expected location data not actual data")
    try:
        logger.info(f"Attempting to determine if car is on {HOME_STREET}")
        gps_only = dict(list(car_gps.items())[:2])
        street = \
            requests.get(f'{GEOAPIFY_URL}?apiKey={GEOAPIFY_KEY}', params=gps_only, timeout=15).json()['features'][0][
                'properties'][
                'street']
        return json.dumps(True) if street == HOME_STREET else json.dumps(False)
    except KeyError as exc:
        logger.error(f"Issue with API: {exc}")
        raise KeyError(f"Error with Geccoding API: {exc}")


@app.get('/')
async def default(request: Request, background_tasks: BackgroundTasks):
    """
    Default function that determines which function to call based on request method.
    this is to be backwards compatible with the old GCP function
    :param request:
    :param background_tasks:
    :return:
    """
    if 'method' in await request.json():
        request_json = await request.json()
        match request_json['method']:
            case 'get_location':
                return await get_location(background_tasks)
            case 'get_proximity':
                return get_proximity(background_tasks)
            case _:
                return {}


def save_gps(gps, vin):
    """
    Save gps to mongodb via Vehicle Data Services
    :param gps:
    :param vin:
    """
    try:
        logger.info("Attempting to save lat lon to mongodb via Vehicle Data Services")
        requests.put(f"{TESLA_DATA_SERVICES_BASE_URL}/api/car/update/gps/{vin}", json=gps, timeout=15)
        logger.info("Sent Put request to Vehicle Data Services to save lat lon to mongodb")
    except Exception as ef:
        logger.error(str(ef))


if __name__ == '__main__':
    print(' ')
    # background_tasks = BackgroundTasks()
    # # print( get_location(background_tasks))
    # # print(get_proximity(background_tasks))
    # # print(is_on_home_street(background_tasks))
