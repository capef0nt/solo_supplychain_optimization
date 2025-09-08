import os
import requests
import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from dotenv import load_dotenv
import json
import urllib.parse
import math
from pymongo import MongoClient

# Load environment variables
load_dotenv()
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

if not USERNAME or not PASSWORD:
    raise ValueError("USERNAME or PASSWORD not found in .env file")

# Database setup
client = MongoClient("mongodb://localhost:27017/")
db = client["buffalo_orders_db"]
collection = db["orders"]

# Endpoints
get_key_url = "https://index.buffaloex.com/buffalo/getRsaPublicKey"
login_url = "https://index.buffaloex.com/buffalo/login"

# Step 0: Create session
session = requests.Session()
session.headers.update({
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Host": "index.buffaloex.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
})

# Step 1: Get RSA key
resp = session.get(get_key_url)
resp.raise_for_status()
public_key_b64 = resp.text.strip()
rsa_key = RSA.import_key(base64.b64decode(public_key_b64))

# Step 2: Encrypt password
cipher = PKCS1_v1_5.new(rsa_key)
encrypted_bytes = cipher.encrypt(PASSWORD.encode("utf-8"))
encrypted_password_encoded = urllib.parse.quote(base64.b64encode(encrypted_bytes).decode("utf-8"), safe='')

# Step 3: Login
login_payload = {"username": USERNAME, "password": encrypted_password_encoded}
login_resp = session.post(login_url, headers={"Content-Type": "application/json;charset=UTF-8"}, data=json.dumps(login_payload))
login_resp.raise_for_status()
ticket = login_resp.json().get("data", {}).get("ticket")
session.headers.update({"Authorization": ticket, "Buffalo-Ticket": ticket})

# Step 4: Get all order IDs
def get_all_order_ids(session):
    page_size = 15
    url = "https://index.buffaloex.com/mobileapi/myorder/orderList?condition=&status=0&pageNum=1&language=en&tableIndex=0&starttime2=&endtime2="
    resp_json = session.get(url).json()
    result_map = resp_json.get("data", {}).get("resultMap", {})
    record_total = result_map.get("recordTotal", 0)
    if record_total == 0:
        return []

    total_pages = math.ceil(record_total / page_size)
    all_order_ids = []

    for page in range(1, total_pages + 1):
        page_url = f"https://index.buffaloex.com/mobileapi/myorder/orderList?condition=&status=0&pageNum={page}&language=en&tableIndex=0&starttime2=&endtime2="
        resp = session.get(page_url).json()
        order_list = resp.get("data", {}).get("resultMap", {}).get("list", [])
        all_order_ids.extend([item["id"] for item in order_list if "id" in item])
    return all_order_ids

order_ids = get_all_order_ids(session)
print(f"Total IDs fetched: {len(order_ids)}")

# Step 5: Fetch order details
def fetch_order_details(order_id, session):
    url = f"https://index.buffaloex.com/mobileapi/myorder/detail/{order_id}?language=en"
    headers = {"Referer": f"https://index.buffaloex.com/client/orders/order-detail?id={order_id}"}
    resp = session.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json().get("data", {})
    print(f"Failed to fetch details for ID {order_id}: {resp.status_code}")
    return None

# Step 6: Clean order data
def clean_order_data(order):
    return {
        "_id": order.get("id"),
        "expressnumber": order.get("expressnumber"),
        "createtimeStr": order.get("createtimeStr"),
        "paystatusname": order.get("paystatusname"),
        "statusname": order.get("statusname"),
        "thirdnumber": order.get("thirdnumber"),
        "updatetimeStr": order.get("updatetimeStr"),
        "receiveaddress": order.get("receiveaddress"),
        "ascertainedweight": order.get("ascertainedweight"),
        "ascertainedvolumweight": order.get("ascertainedvolumweight"),
        "ascertainedcost": order.get("ascertainedcost"),
        "receivedtax": order.get("receivedtax"),
        "displaytime": order.get("displaytime"),
        "boxList": [
            {"number": detail.get("number"), "declaredvalue": detail.get("declaredvalue")}
            for box in order.get("boxList", [])
            for detail in box.get("detaillist", [])
        ],
        "recordMap": [
            {"id": rec.get("id"), "createtime": rec.get("createtime"), "content": rec.get("content"), "expressid": rec.get("expressid")}
            for rec in order.get("recordMap", [])
        ]
    }

# Step 7: Fetch, clean, and save all orders
for order_id in order_ids:
    raw_order = fetch_order_details(order_id, session)
    if raw_order:
        print(raw_order)
        cleaned_order = clean_order_data(raw_order)
        collection.update_one({"_id": cleaned_order["_id"]}, {"$set": cleaned_order}, upsert=True)

print("All orders fetched, cleaned, and saved to database.")
