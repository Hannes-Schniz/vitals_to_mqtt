import psutil
import json
import datetime
import socket
import paho.mqtt.client as mqtt

MQTT_BROKER = "192.168.188.74"    # Change to your broker address if needed
MQTT_PORT = 1883
MQTT_TOPIC = "system/processes"

def get_processes_info():
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_info', 'status', 'create_time']):
        try:
            info = proc.info
            if info["memory_info"]:
                info["memory_info"] = dict(info["memory_info"]._asdict())
            processes.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return processes

def main():
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    hostname = socket.gethostname()
    filename = f"process_dump_{hostname}_{now}.json"

    processes = get_processes_info()
    data = {
        "timestamp": now,
        "hostname": hostname,
        "processes": processes
    }

    # Write to file
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

    # Publish to MQTT anonymously (no username/password)
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.publish(MQTT_TOPIC, json.dumps(data))
    client.disconnect()

    print(f"Process dump written to {filename} and published to MQTT topic {MQTT_TOPIC}")

if __name__ == "__main__":
    main()
