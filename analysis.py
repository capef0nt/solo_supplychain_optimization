from pymongo import MongoClient
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import numpy as np
from datetime import datetime


# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["buffalo_orders_db"]
collection = db["orders"]

# Fetch all orders
orders = list(collection.find({}))

# Convert to DataFrame
df = pd.DataFrame(orders)

from datetime import datetime

def parse_order(order):
    # --- Parse recordMap to get stage durations ---
    record_map = order.get("recordMap", [])
    # Sort by createtime
    record_map_sorted = sorted(record_map, key=lambda x: x["createtime"])
    
    stage_times = []
    for i in range(1, len(record_map_sorted)):
        prev = record_map_sorted[i-1]
        curr = record_map_sorted[i]
        # convert timestamps (ms) to datetime
        prev_time = datetime.fromtimestamp(prev["createtime"] / 1000)
        curr_time = datetime.fromtimestamp(curr["createtime"] / 1000)
        duration = (curr_time - prev_time).total_seconds() / 3600  # hours
        stage_times.append({
            "from": prev["content"],
            "to": curr["content"],
            "duration_hours": duration
        })
    
    # --- Parse boxList to get total items and declared value ---
    total_items = 0
    total_declared_value = 0.0
    box_list = order.get("boxList", [])
    for box in box_list:
        for detail in box.get("detaillist", []):
            total_items += detail.get("number", 0)
            total_declared_value += detail.get("declaredvalue", 0.0)
    
    return {
        "order_id": order.get("_id"),
        "stage_times": stage_times,
        "total_items": total_items,
        "total_declared_value": total_declared_value,
        "ascertainedweight": order.get("ascertainedweight"),
        "ascertainedcost": order.get("ascertainedcost")
    }

# --- Fetch all cleaned orders ---
orders = list(collection.find({}))

# --- Parse each order ---
parsed_orders = [parse_order(order) for order in orders]

# --- Flatten data for analysis ---
rows = []
for order in parsed_orders:
    order_id = order["order_id"]
    for stage in order["stage_times"]:
        rows.append({
            "order_id": order_id,
            "from_stage": stage["from"],
            "to_stage": stage["to"],
            "duration_hours": stage["duration_hours"],
            "total_items": order["total_items"],
            "total_declared_value": order["total_declared_value"],
            "ascertainedweight": float(order["ascertainedweight"] or 0),
            "ascertainedcost": float(order["ascertainedcost"] or 0)
        })

# --- Create DataFrame ---
df = pd.DataFrame(rows)
pd.set_option('display.max_columns', None)
print(df.head())