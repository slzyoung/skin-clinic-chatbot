import urllib.request
import json

batch_id = "9d236439-4953-4a59-bb7f-f050cb6f2b87"
url = f"http://127.0.0.1:8000/api/knowledge/batch/{batch_id}"

print(f"Testing batch URL: {url}")
try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print(f"SUCCESS! Status: {resp.status}")
        print(f"Returned {len(data)} documents for batch {batch_id}")
        for item in data:
            print(f" - ID: {item.get('id')}, Title: {item.get('title')}, Status: {item.get('status')}")
except Exception as e:
    print(f"Error fetching batch endpoint: {e}")
