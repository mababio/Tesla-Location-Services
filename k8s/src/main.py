import math
import googlemaps
import teslapy
from flask import Flask, request
import os
import notification

"""
   wrapper around the TeslaPy Python module that returns car's location in lat,lon format
   :param request: internal gcp Function param
   :return: location if available
"""

app = Flask(__name__)

LAT_HOME = float(os.environ.get("LAT_HOME"))
LON_HOME = float(os.environ.get("LON_HOME"))
HOME_RADIUS = float(os.environ.get("HOME_RADIUS"))
TESLA_USERNAME = os.environ.get("TESLA_USERNAME")
HOME_STREET = os.environ.get("HOME_STREET")
GMAPS_KEY = os.environ.get("GMAPS_KEY")


@app.route('/')
def default():
    if 'method' in request.get_json():
        match request.get_json()['method']:
            case 'get_location':
                return get_location()
            case 'get_proximity':
                return get_proximity()
            case _:
                return {}


# TODO: In the event that person has multiple cars, we can add param to select Car. It can be on vin, display name.

@app.route('/get_location', methods=['GET'])
def get_location():
    with teslapy.Tesla(TESLA_USERNAME) as tesla:
        wanted_key = 'drive_state'
        vehicles = tesla.vehicle_list()
        timeout = 7
        try:
            vehicles[0].sync_wake_up(timeout)
            tesla_data = vehicles[0].api('VEHICLE_DATA')
        except teslapy.VehicleError as e:
            notification.send_push_notification(f"Timeout of {timeout} second for car to wake was reached:{e}")
            raise teslapy.VehicleError

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
    gmaps = googlemaps.Client(key=GMAPS_KEY)
    reverse_geocode_result = gmaps.reverse_geocode((lat, lon))
    for i in reverse_geocode_result:
        if HOME_STREET in i['address_components'][0]['long_name']:
            return True
    return False


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
