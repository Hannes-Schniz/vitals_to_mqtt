import psutil
import json
import datetime
import socket
import requests
import time

INFLUXDB_CREDS_FILE = "influxdb_secrets"  # Path to your credentials file

def read_influxdb_credentials(filepath=INFLUXDB_CREDS_FILE):
    creds = {}
    try:
        with open(filepath, "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    creds[key.strip()] = value.strip()
    except Exception as e:
        print(f"Failed to read InfluxDB credentials: {e}")
        return None
    required_keys = {"url", "token", "org", "bucket"}
    if not required_keys <= creds.keys():
        print(f"InfluxDB credentials file missing required keys: {required_keys - creds.keys()}")
        return None
    return creds

def get_processes_info():
    processes = []
    proc_objs = []
    skipped = 0
    num_cpus = psutil.cpu_count(logical=True)
    # First pass: collect process objects and prime cpu_percent
    for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_info', 'status', 'create_time']):
        try:
            proc.cpu_percent(interval=None)
            proc_objs.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            skipped += 1
            continue
    time.sleep(0.1)  # Wait a bit to get accurate CPU percent

    # Second pass: collect info including actual cpu_percent
    for proc in proc_objs:
        try:
            info = proc.as_dict(attrs=['pid', 'name', 'username', 'memory_info', 'status', 'create_time'])
            # Get absolute CPU percent (relative to all CPUs)
            cpu_percent = proc.cpu_percent(interval=None)
            if num_cpus and num_cpus > 0:
                cpu_percent = cpu_percent / num_cpus
            info['cpu_percent'] = round(cpu_percent, 2)
            if info["memory_info"]:
                # Show RSS and VMS in rounded KB
                info["memory_rss"] = round(info["memory_info"].rss / 1024)
                info["memory_vms"] = round(info["memory_info"].vms / 1024)
                del info["memory_info"]
            processes.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            skipped += 1
            continue
    if skipped > 0:
        print(f"Warning: Skipped {skipped} processes due to permission errors. Try running as root to see all processes.")
    return processes

def send_to_influxdb(processes, creds, measurement="process_stats"):
    lines = []
    hostname = socket.gethostname()
    timestamp_ns = int(datetime.datetime.now(datetime.UTC).timestamp() * 1e9)
    for p in processes:
        tags = [
            f'host={hostname}',
            f'pid={p.get("pid", 0)}',
            f'username={p.get("username", "").replace(" ", "_")}',
            f'name={p.get("name", "").replace(" ", "_")}',
            f'status={p.get("status", "").replace(" ", "_")}'
        ]
        fields = [
            f'cpu_percent={p.get("cpu_percent", 0)}',
            f'memory_rss={p.get("memory_rss", 0)}i',
            f'memory_vms={p.get("memory_vms", 0)}i'  # Now in KB, rounded
        ]
        line = (f'{measurement},{",".join(tags)} {",".join(fields)} {timestamp_ns}')
        lines.append(line)

    body = "\n".join(lines)
    url = f"{creds['url'].rstrip('/')}/api/v2/write?org={creds['org']}&bucket={creds['bucket']}&precision=ns"
    headers = {
        "Authorization": f"Token {creds['token']}",
        "Content-Type": "text/plain; charset=utf-8"
    }
    try:
        resp = requests.post(url, headers=headers, data=body)
        if resp.status_code >= 300:
            print(f"Failed to write to InfluxDB: {resp.status_code} {resp.text}")
        else:
            print("Process data successfully sent to InfluxDB")
    except Exception as e:
        print(f"Error sending to InfluxDB: {e}")

def main():
    now = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
    hostname = socket.gethostname()
    filename = f"process_dump_{hostname}_{now}.json"

    creds = read_influxdb_credentials()
    if not creds:
        print("InfluxDB credentials missing or invalid.")
        return

    processes = get_processes_info()
    data = {
        "timestamp": now,
        "hostname": hostname,
        "processes": processes
    }

    # Write to file for auditing/debugging
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

    # Send to InfluxDB
    send_to_influxdb(processes, creds)

if __name__ == "__main__":
    main()