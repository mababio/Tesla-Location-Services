import requests
# sess = requests.Session()
# adapter = requests.adapters.HTTPAdapter(max_retries=20)
# sess.mount('http://', adapter)
response_obj = requests.get('http://localhost:8080/get_location')
if response_obj.status_code == 200:
    print(response_obj.json()['speed'])
