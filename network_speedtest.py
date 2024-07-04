import speedtest
import datetime
from termcolor import colored
import emoji
from ping3 import ping
import socket
import requests
import platform

def calculate_packet_loss(host_ip, count=4):
    """Calculate the packet loss percentage by pinging a host IP multiple times."""
    responses = [ping(host_ip) for _ in range(count)]
    lost_packets = responses.count(None)
    packet_loss_percentage = (lost_packets / count) * 100
    return packet_loss_percentage

def calculate_ping_statistics(host_ip, count=4):
    """Calculate ping statistics including low, high, average, and jitter."""
    pings = []
    for _ in range(count):
        try:
            response = ping(host_ip)
            if response is not None:
                pings.append(response)
        except Exception as e:
            print(colored(f"Ping error: {e}", "red"))

    if not pings:
        return 'N/A', 'N/A', 'N/A', 'N/A'
    
    pings = [p * 1000 for p in pings]  # Convert to milliseconds
    low = min(pings)
    high = max(pings)
    avg = sum(pings) / len(pings)
    jitter = high - low
    return low, high, avg, jitter

def get_connection_type():
    """Retrieve the connection type using the ipinfo.io API."""
    try:
        response = requests.get("https://ipinfo.io", timeout=5)
        data = response.json()
        return data.get('org', 'Unknown Provider')
    except requests.RequestException:
        return 'Unknown Provider'

def get_internal_ip():
    """Get the internal IP address of the current device."""
    return socket.gethostbyname(socket.gethostname())

def get_external_ip():
    """Get the external IP address using the api.ipify.org API."""
    try:
        response = requests.get("https://api.ipify.org", timeout=5)
        return response.text
    except requests.RequestException:
        return 'N/A'

def get_device_type():
    """Get the type of device (OS and version)."""
    return platform.system() + " " + platform.release()

def get_location():
    """Get the geographical location using the ipinfo.io API."""
    try:
        response = requests.get("https://ipinfo.io", timeout=5)
        data = response.json()
        return data.get('loc', 'N/A')
    except requests.RequestException:
        return 'N/A'

def resolve_host_ip(host):
    """Resolve the IP address of the host."""
    try:
        return socket.gethostbyname(host)
    except socket.gaierror:
        return None

def perform_speedtest_with_retries(st, test_type, retries):
    """Perform speedtest with specified retries for download or upload."""
    for attempt in range(retries):
        try:
            if test_type == 'download':
                speed = st.download() / 1_000_000  # Convert to Mbps
                data_used = st.results.bytes_received / 1_000_000  # Convert to MB
            elif test_type == 'upload':
                speed = st.upload() / 1_000_000  # Convert to Mbps
                data_used = st.results.bytes_sent / 1_000_000  # Convert to MB
            return speed, data_used
        except speedtest.SpeedtestException as e:
            print(colored(f"Speedtest exception during {test_type} test (attempt {attempt + 1}/{retries}): {e} ❌", "red"))
    print(colored(f"{test_type.capitalize()} test failed after {retries} attempts. ❌", "red"))
    return None, None

def perform_speedtest(num_tests=1, retries=3, ping_retries=3):
    """Main function to perform the speedtest, handle retries, and display results."""
    try:
        st = speedtest.Speedtest()
    except Exception as e:
        print(colored(f"Failed to retrieve configuration: {e} ❌", "red"))
        return

    best_server = None
    for _ in range(ping_retries):
        try:
            print(colored("Selecting the best server... 🔍", "blue"))
            best_server = st.get_best_server()
            if not best_server:
                print(colored("No servers available. ❌", "red"))
                continue
            server_host = best_server.get('host', 'N/A').split(':')[0]  # Remove port if present
            server_ip = resolve_host_ip(server_host)
            if not server_ip:
                print(colored(f"Failed to resolve server IP for {server_host}. ❌", "red"))
                continue
            server_name = best_server.get('name', 'N/A')
            server_country = best_server.get('country', 'N/A')
            server_latency = best_server.get('latency', 'N/A')
            # Try pinging the server
            ping_response = ping(server_ip)
            if ping_response is None:
                print(colored(f"Failed to ping server {server_host} ({server_ip}). Trying another server... ❌", "red"))
                continue
            print(colored(f"Selected Server: {server_host} ({server_ip}) located in {server_name}, {server_country} (Latency: {server_latency} ms) 🌐", "green"))
            break
        except Exception as e:
            print(colored(f"Failed to retrieve server: {e} ❌", "red"))

    if not best_server:
        print(colored("Failed to find a suitable server after multiple attempts. ❌", "red"))
        return

    total_download_speed = 0
    total_upload_speed = 0
    total_download_data = 0
    total_upload_data = 0
    successful_tests = 0

    for i in range(num_tests):
        print(colored(f"Testing download speed (test {i + 1}/{num_tests})... ⬇️", "blue"))
        download_speed, download_data = perform_speedtest_with_retries(st, 'download', retries)
        if download_speed and download_data:
            total_download_speed += download_speed
            total_download_data += download_data
            print(colored(f"Download test {i + 1} complete: {download_speed:.2f} Mbps 🎉 (Data Used: {download_data:.2f} MB)", "green"))
        else:
            continue

        print(colored(f"Testing upload speed (test {i + 1}/{num_tests})... ⬆️", "blue"))
        upload_speed, upload_data = perform_speedtest_with_retries(st, 'upload', retries)
        if upload_speed and upload_data:
            total_upload_speed += upload_speed
            total_upload_data += upload_data
            print(colored(f"Upload test {i + 1} complete: {upload_speed:.2f} Mbps 🎉 (Data Used: {upload_data:.2f} MB)", "green"))

        successful_tests += 1

    if successful_tests == 0:
        print(colored("All tests failed. ❌", "red"))
        return

    avg_download_speed = total_download_speed / successful_tests
    avg_upload_speed = total_upload_speed / successful_tests
    avg_download_data = total_download_data / successful_tests
    avg_upload_data = total_upload_data / successful_tests

    # Fallback ping test
    if server_ip is None or not any(ping(server_ip) for _ in range(ping_retries)):
        server_ip = resolve_host_ip("google.com")

    packet_loss = calculate_packet_loss(server_ip)
    idle_low, idle_high, idle_avg, idle_jitter = calculate_ping_statistics(server_ip)
    download_low, download_high, download_avg, download_jitter = calculate_ping_statistics(server_ip)
    upload_low, upload_high, upload_avg, upload_jitter = calculate_ping_statistics(server_ip)

    connection_type = get_connection_type()
    internal_ip = get_internal_ip()
    external_ip = get_external_ip()
    device_type = get_device_type()
    location = get_location()

    now = datetime.datetime.now().strftime("%B %d, %Y @ %I:%M %p")

    def pad(text, width):
        return text + ' ' * (width - len(text))

    def format_value(value):
        return f"{value:.2f}" if isinstance(value, (int, float)) else value

    max_width = max(len(now),
                    len(f"Server: {server_host} ({server_ip}) (Latency: {server_latency:.3f} ms)"),
                    len(f"Server Location: {server_name}, {server_country}"),
                    len(f"Connection Type: {connection_type}"),
                    len(f"Device: {device_type}"),
                    len(f"Internal IP: {internal_ip}"),
                    len(f"External IP: {external_ip}"),
                    len(f"Location: {location}"),
                    len(f"Download (avg): {avg_download_speed:.2f} Mbps (Data Used: {avg_download_data:.2f} MB)"),
                    len(f"Upload (avg): {avg_upload_speed:.2f} Mbps (Data Used: {avg_upload_data:.2f} MB)"),
                    len(f"Packet Loss: {packet_loss:.2f}%"),
                    len(f"Idle (avg): {format_value(idle_avg)} ms (Low: {format_value(idle_low)} ms, High: {format_value(idle_high)} ms, Jitter: {format_value(idle_jitter)} ms)"),
                    len(f"Download Ping (avg): {format_value(download_avg)} ms (Low: {format_value(download_low)} ms, High: {format_value(download_high)} ms, Jitter: {format_value(download_jitter)} ms)"),
                    len(f"Upload Ping (avg): {format_value(upload_avg)} ms (Low: {format_value(upload_low)} ms, High: {format_value(upload_high)} ms, Jitter: {format_value(upload_jitter)} ms)"))

    print(f"+{'-' * (max_width + 2)}+")
    print(f"| {pad('Date: ' + now, max_width)} |")
    print(f"| {pad(f'Server: {server_host} ({server_ip}) (Latency: {server_latency:.3f} ms)', max_width)} |")
    print(f"| {pad(f'Server Location: {server_name}, {server_country}', max_width)} |")
    print(f"+{'-' * (max_width + 2)}+")
    print(f"| {pad(f'Connection Type: {connection_type}', max_width)} |")
    print(f"| {pad(f'Device: {device_type}', max_width)} |")
    print(f"| {pad(f'Internal IP: {internal_ip}', max_width)} |")
    print(f"| {pad(f'External IP: {external_ip}', max_width)} |")
    print(f"| {pad(f'Location: {location}', max_width)} |")
    print(f"+{'-' * (max_width + 2)}+")
    print(f"| {pad(f'Download (avg): {avg_download_speed:.2f} Mbps (Data Used: {avg_download_data:.2f} MB)', max_width)} |")
    print(f"| {pad(f'Upload (avg): {avg_upload_speed:.2f} Mbps (Data Used: {avg_upload_data:.2f} MB)', max_width)} |")
    print(f"+{'-' * (max_width + 2)}+")
    print(f"| {pad(f'Packet Loss: {packet_loss:.2f}%', max_width)} |")
    print(f"| {pad(f'Idle (avg): {format_value(idle_avg)} ms (Low: {format_value(idle_low)} ms, High: {format_value(idle_high)} ms, Jitter: {format_value(idle_jitter)} ms)', max_width)} |")
    print(f"| {pad(f'Download Ping (avg): {format_value(download_avg)} ms (Low: {format_value(download_low)} ms, High: {format_value(download_high)} ms, Jitter: {format_value(download_jitter)} ms)', max_width)} |")
    print(f"| {pad(f'Upload Ping (avg): {format_value(upload_avg)} ms (Low: {format_value(upload_low)} ms, High: {format_value(upload_high)} ms, Jitter: {format_value(upload_jitter)} ms)', max_width)} |")
    print(f"+{'-' * (max_width + 2)}+")

    try:
        with open("speedtest_results.log", "a") as log:
            log.write(f"{now}: Selected Server: {server_host} ({server_ip}) located in {server_name}, {server_country} (Latency: {server_latency} ms), "
                      f"Average Download: {avg_download_speed:.2f} Mbps (Data Used: {avg_download_data:.2f} MB), "
                      f"Average Upload: {avg_upload_speed:.2f} Mbps (Data Used: {avg_upload_data:.2f} MB), "
                      f"Packet Loss: {packet_loss:.2f}%, "
                      f"Idle (avg): {format_value(idle_avg)} ms (Low: {format_value(idle_low)} ms, High: {format_value(idle_high)} ms, Jitter: {format_value(idle_jitter)} ms), "
                      f"Download Ping (avg): {format_value(download_avg)} ms (Low: {format_value(download_low)} ms, High: {format_value(download_high)} ms, Jitter: {format_value(download_jitter)} ms), "
                      f"Upload Ping (avg): {format_value(upload_avg)} ms (Low: {format_value(upload_low)} ms, High: {format_value(upload_high)} ms, Jitter: {format_value(upload_jitter)} ms), "
                      f"Connection Type: {connection_type}, Device: {device_type}, Internal IP: {internal_ip}, External IP: {external_ip}, Location: {location}\n")
    except Exception as e:
        print(colored(f"Failed to log results: {e} ❌", "red"))

if __name__ == "__main__":
    perform_speedtest(num_tests=3, retries=3)
