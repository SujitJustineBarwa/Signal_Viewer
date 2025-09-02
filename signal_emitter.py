import redis
import time
import random
from datetime import datetime
from pytz import timezone
import numpy as np
import os

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, db=0)

# Define multiple signal stream names
signal_names = ["signal_A", "signal_B","signal_C"]

# Initialize starting values for each signal
signal_values = {name: 100.0 for name in signal_names}

try:
    while True:
        os.system('clear')
        for name in signal_names:
            # Simulate geometric random walk: S_t+1 = S_t * exp(mu + sigma * Z)
            mu = 0.0005
            sigma = 0.01
            Z = np.random.normal()
            signal_values[name] *= np.exp(mu + sigma * Z)
            
            ist = timezone('Asia/Kolkata')
            data = {
                "timestamp": datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S"),
                "value": str(signal_values[name])
            }

            # Add to Redis stream
            r.xadd(name, data, maxlen=100, approximate=False)
            print(f"Streamed to {name}: \n    Timestamp: {data['timestamp']} \n    Value: {data['value']}")

        # Wait 1 second
        time.sleep(1)

except KeyboardInterrupt:
        print("Stopped streaming.")