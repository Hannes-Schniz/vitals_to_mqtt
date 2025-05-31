# 🖥️ System Vitals to MQTT 🚀

A Bash script to collect system vitals (CPU/GPU temperature, fan speeds, memory, load, and all mounted drives) from an Ubuntu 24.04 machine and publish them as a JSON payload to an MQTT broker. This is useful for monitoring your Linux system from a central location, such as Home Assistant, Node-RED, or any MQTT-compatible dashboard.

## ✨ Features

- Publishes the following system vitals:
  - 🏷️ Hostname, 🕒 current time, and ⏳ uptime
  - 🧠 CPU load, 🌡️ temperature, and 🌀 fan speed
  - 🎮 GPU temperature and fan speed (supports NVIDIA, partial support for others)
  - 💾 Memory total, used, and available
  - 📦 All mounted drives (used, available, size per mount point)
- Sends JSON data to a configurable MQTT broker/topic 📤
- 🔒 MQTT credentials are securely read from a secrets file
- 🕰️ Suitable for scheduling via cron or systemd

## 🛠️ Prerequisites

Install required packages:
```bash
sudo apt update
sudo apt install -y mosquitto-clients jq bc lm-sensors pciutils
```

- For NVIDIA GPU support, install the proprietary NVIDIA drivers (`nvidia-smi` must work).
- For other GPUs, ensure you have necessary kernel modules or tools for `sensors`.
- Run `sudo sensors-detect` and follow the prompts to set up hardware monitoring.
- Secure your secrets file as described below.

## ⚡ Setup

1. **Clone or download this repository.**

2. **Configure your MQTT secrets:**  
   Create the secrets file `/etc/mqtt_secrets` with the following content:
   ```bash
   MQTT_USERNAME="your_username"
   MQTT_PASSWORD="your_password"
   ```
   Secure the file:
   ```bash
   sudo chmod 600 /etc/mqtt_secrets
   ```

3. **Edit the script:**  
   Open `system_vitals_to_mqtt.sh` and set your MQTT broker address, port, and topic at the top of the script.

4. **Make the script executable:**
   ```bash
   chmod +x system_vitals_to_mqtt.sh
   ```

5. **Test the script:**
   ```bash
   ./system_vitals_to_mqtt.sh
   ```

6. **Automate (Optional):**
   - To send data periodically, add a cron job (e.g. every 5 minutes):
     ```bash
     crontab -e
     ```
     Add:
     ```
     */5 * * * * /path/to/system_vitals_to_mqtt.sh
     ```
   - Or use a systemd timer for finer control.

## 📦 Example MQTT Payload

```json
{
  "hostname": "my-ubuntu-pc",
  "time": "2025-05-31T12:04:25+00:00",
  "uptime_s": 123456,
  "cpu_load": 0.15,
  "cpu_temp_C": 43.0,
  "cpu_fan_speed_rpm": 1200,
  "gpu_temp_C": 38,
  "gpu_fan_speed_percent": 30,
  "mem_total_kb": 16392000,
  "mem_used_kb": 4500000,
  "mem_available_kb": 11892000,
  "drives": [
    {"mount":"/","used":"5G","available":"20G","size":"25G"},
    {"mount":"/home","used":"100G","available":"400G","size":"500G"}
  ]
}
```

*Note: Some fields may show `"N/A"` if not available for your hardware.*

## 🔒 Security

- **Do not commit your secrets file** to version control! 🚫
- The script reads MQTT credentials from `/etc/mqtt_secrets` with permissions `600`.

## 📄 License

MIT License. See [LICENSE](LICENSE).

## 🐞 Troubleshooting

- If you don’t see temperature or fan data, ensure you’ve run `sudo sensors-detect` and rebooted.
- For GPU data, ensure you have the correct drivers and utilities installed.
- Check your MQTT broker configuration and network connectivity if messages aren’t arriving.

---

💡 *Contributions and improvements welcome!*
