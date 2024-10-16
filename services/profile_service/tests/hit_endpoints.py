import requests


response = requests.get("http://localhost:5002/get_user_info",params={'user_id': 1})
post_info = response.json()
print(post_info)
assert response.status_code == 200

response = requests.post("http://localhost:5002/insert_new_user",json={'user_name': "Vishnu"})
post_info = response.json()
print(post_info)
assert response.status_code == 200


