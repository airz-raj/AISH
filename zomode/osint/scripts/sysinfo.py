from check_requirements import check_modules
check_modules()

import platform, psutil, socket, os

print("System:", platform.system())
print("Release:", platform.release())
print("Version:", platform.version())
print("Architecture:", platform.machine())
print("Processor:", platform.processor())

print("\nCPU Cores:", psutil.cpu_count(logical=False))
print("Logical CPUs:", psutil.cpu_count(logical=True))
print("CPU Usage:", psutil.cpu_percent(interval=1), "%")

print("\nMemory Total:", round(psutil.virtual_memory().total / (1024**3), 2), "GB")
print("Memory Available:", round(psutil.virtual_memory().available / (1024**3), 2), "GB")

print("\nDisk Partitions:")
for part in psutil.disk_partitions():
    usage = psutil.disk_usage(part.mountpoint)
    print(f"  {part.device} -> {usage.percent}% used")

print("\nNetwork Info:")
hostname = socket.gethostname()
print("Hostname:", hostname)
print("Local IP:", socket.gethostbyname(hostname))