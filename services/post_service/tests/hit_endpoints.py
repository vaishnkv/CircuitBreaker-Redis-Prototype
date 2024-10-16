import requests


response = requests.get("http://localhost:5001/get_post_info",params={'post_id': 1})
post_info = response.json()
print(post_info)
assert response.status_code == 200

response = requests.post("http://localhost:5001/insert_post",json={'user_id': 1,"content": "New post content!"})
post_info = response.json()
print(post_info)
assert response.status_code == 200


