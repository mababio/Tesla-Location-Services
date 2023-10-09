import math
import googlemaps
import requests
import teslapy
from config import settings
from flask import Flask, request
import os

"""
   wrapper around the TeslaPy Python module that returns car's location in lat,lon format
   :param request: internal gcp Function param
   :return: location if available
"""

app = Flask(__name__)


@app.route('/')
def default():
    if 'method' in request.get_json():
        match request.get_json()['method']:
            case 'get_location':
                return get_location()
            case 'get_proximity':
                return get_proximity()


@app.route('/get_location', methods=['GET'])
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
            lat = float(drive_state['latitude'])
            lon = float(drive_state['longitude'])
            return {'lat': lat, 'lon': lon, 'speed': drive_state['speed']}


@app.route('/get_proximity', methods=['GET'])
def get_proximity():
    if 'lat' not in request.get_json() or 'lon' not in request.get_json():
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

        return data
    else:
        data['is_close'] = False
        data['is_on_arcuri'] = False
        return data
        # json_data = json.dumps(data)
        # return json_data


def is_on_home_street(lat, lon):
    gmaps = googlemaps.Client(key=settings['tesla-location-services']['gmaps']['key'])
    reverse_geocode_result = gmaps.reverse_geocode((lat, lon))
    for i in reverse_geocode_result:
        if settings['tesla-location-services']['home_street'] in i['address_components'][0]['long_name']:
            return True
    return False


# def tesla_location_services(request):
#     match request.get_json()['method']:
#         case 'get_location':
#             return get_location()
#         case 'get_proximity':
#             if 'lat' in request.get_json() and 'lon' in request.get_json():
#                 return get_proximity(request.get_json['lat'], request.get_json['lon'])
#             else:
#                 return get_proximity()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
