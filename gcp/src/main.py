import math
import time

import googlemaps
import teslapy
import json
from config import settings

"""
   wrapper around the TeslaPy Python module that returns car's location in lat,lon format
   :param request: internal gcp Function param
   :return: location if available
   """


def get_location():
    with teslapy.Tesla(settings['production']['tesla']['username']) as tesla:
        wanted_key = 'drive_state'
        vehicles = tesla.vehicle_list()
        vehicles[0].sync_wake_up(1.5)
        tesla_data = vehicles[0].api('VEHICLE_DATA')
        if type(tesla_data) is not teslapy.JsonDict or wanted_key not in tesla_data['response']:
            return []
        else:
            drive_state = tesla_data['response'][wanted_key]
            lat = str(drive_state['latitude'])
            lon = str(drive_state['longitude'])
            return {'lat': lat, 'lon': lon, 'speed': drive_state['speed']}


def is_on_home_street(lat, lon):
    gmaps = googlemaps.Client(key=settings['tesla-location-services']['gmaps']['key'])
    reverse_geocode_result = gmaps.reverse_geocode((lat, lon))
    for i in reverse_geocode_result:
        if settings['tesla-location-services']['home_street'] in i['address_components'][0]['long_name']:
            return True
    return False


def get_proximity(lat=None, lon=None):
    if lat is None or lon is None:
        latlon = get_location()
        lat = latlon['lat']
        lon = latlon['lon']

    radius = 6371
    d_lat = math.radians(lat - settings['production']['LAT_HOME'])
    d_lon = math.radians(lon - settings['production']['LON_HOME'])
    a = math.sin(d_lat / 2) * math.sin(d_lat / 2) + math.cos(
        math.radians(settings['production']['LAT_HOME'])) * math.cos(math.radians(lat)) * \
        math.sin(d_lon / 2) * math.sin(d_lon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    difference = radius * c
    str_difference = float(difference)
    data = {'difference': str_difference}

    if difference < settings['production']['HOME_RADIUS'] \
            or math.isclose(difference, settings['production']['HOME_RADIUS']):
        data['is_close'] = True
        if is_on_home_street(lat, lon):
            data['is_on_arcuri'] = True
        else:
            data['is_on_arcuri'] = False

        json_data = json.dumps(data)
        return json_data
    else:
        data['is_close'] = False
        data['is_on_arcuri'] = False
        json_data = json.dumps(data)
        return json_data


def tesla_location_services(request):
    match request.get_json()['method']:
        case 'get_location':
            return get_location()
        case 'get_proximity':
            if request.get_json['lat'] and request.get_json()['lon']:
                return get_proximity(request.get_json['lat'], request.get_json['lon'])
            else:
                return get_proximity()


# if __name__ == "__main__":
#     count = 0
#     while True:
#         count += 1
#         print(count)
#         print(tesla_get_location(''))
#         time.sleep(5)
