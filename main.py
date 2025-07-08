import os
from microdot import Microdot
import network
from time import sleep
from machine import Pin, I2C, reset
import json
from picozero import pico_led
import gc

import ahtx0

ssid = 'MY_WIFI'
password = 'MY_WIFI_PASSWORD'

i2c = I2C(0, scl=Pin(17), sda=Pin(16), freq=400000)

sensor = ahtx0.AHT10(i2c)

def connect():
    """Connect to WLAN"""
    print("Starting WiFi connection...")
    pico_led.off()
    sleep(0.2)
    pico_led.on()
    sleep(0.2)
    pico_led.off()
    sleep(0.2)
    pico_led.on()
    sleep(0.2)
    pico_led.off()
    sleep(4)
    
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    sleep(0.2)
    wlan.active(True)
    sleep(0.2)
    
    attempt_i = 1
    max_attempts = 10
    
    print(f'Connecting to WiFi: {ssid}')
    wlan.connect(ssid, password)
    
    while wlan.isconnected() == False and attempt_i <= max_attempts:
        pico_led.on()
        sleep(0.5)
        pico_led.off()
        sleep(0.5)
        print(f'Waiting for connection... Attempt: {attempt_i}/{max_attempts}')
        sleep(5)
        wlan.connect(ssid, password)
        attempt_i += 1
    
    if wlan.isconnected():
        pico_led.on()
        sleep(1)
        ip = wlan.ifconfig()[0]
        print(f'✓ Connected! IP: {ip}')
        return True
    else:
        print(f'✗ Failed to connect after {max_attempts} attempts')
        return False

def get_data(gimme_raw = False):
    sleep(0.2)
    pico_led.on()
    sleep(0.2)
    pico_led.off()
    sleep(0.2)
    pico_led.on()
    sleep(0.2)
    pico_led.off()
    
    # Get them sensor readings
    temp_celsius_raw = sensor.temperature
    humidity_raw = sensor.relative_humidity
    
    # Process temperature
    if temp_celsius_raw is not None:
        temp_celsius = int(temp_celsius_raw)
        temp_farenheit = int((temp_celsius_raw * 9/5) + 32)
        temp_farenheit_raw = (temp_celsius_raw * 9/5) + 32
        print("Temperature: %f" % temp_farenheit)
    else:
        temp_celsius = temp_celsius_raw = temp_farenheit = temp_farenheit_raw = 0
    
    if humidity_raw is not None:
        humidity = int(humidity_raw)
        print("Humidity: %f %%" % humidity_raw)
    else:
        humidity = humidity_raw = 0
    
    if gimme_raw == True:
        response = {"humidity":humidity_raw,"temp_farenheit":temp_farenheit_raw, "temp_celsius":temp_celsius_raw}
    else:
        response = {"humidity":str(humidity),"temp_farenheit":str(temp_farenheit),"temp_celsius":str(temp_celsius)}
    return response

def reset_sensor():
    # Manually reset the AHTx0 sensor
    try:
        global sensor, i2c
        print("Resetting sensor...")
        sensor = ahtx0.AHT10(i2c)
        sleep(2)
        
        for i in range(3):
            temp = sensor.temperature
            hum = sensor.relative_humidity
            print(f"Readings... {i+1}: Temp={temp}°C, Humidity={hum}%")
            sleep(1)
            
        print("Sensor reset complete")
        return True
    except Exception as e:
        print(f"Sensor reset failed: {e}")
        return False

def cleanup_sockets():
    # Cleanup "stuck" sockets
    try:
        import usocket as socket
        print("Attempting socket cleanup...")
        for i in range(5):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('0.0.0.0', 5001))
                sock.close()
                print(f"Socket {i} cleaned up")
                break
            except Exception as e:
                print(f"Socket {i} cleanup failed: {e}")
                pass
    except Exception as e:
        print(f"Socket cleanup error: {e}")

def main():
    print("=" * 20)
    print("Starting Pico 2W Temperature Server")
    print("=" * 20)
    
    # garbage collect before get started
    gc.collect()
    print(f"Free memory: {gc.mem_free()} bytes")
    
    # Connect to WiFi if needed
    if not connect():
        print("WiFi connection failed, resetting...")
        sleep(5)
        reset()
        return
    
    # Initialize microdot server
    app = Microdot()
    
    @app.route('/')
    def index(request):
        print("GET / - Serving sensor data")
        response = get_data()
        return response, 200, {'Content-Type': 'application/json'}

    @app.route('/list')
    def list_data(request):
        print("GET /list - Serving sensor data as list")
        response = get_data()
        return [response], 200, {'Content-Type': 'application/json'}
    
    @app.route('/raw')
    def raw_data(request):
        print("GET /raw - Serving raw sensor data")
        response = get_data(True)
        return response, 200, {'Content-Type': 'application/json'}

    @app.get('/shutdown')
    async def shutdown(request):
        print("Shutdown requested")
        request.app.shutdown()
        return 'Server shutting down...'
    
    @app.route('/reset-sensor')
    def reset_sensor_endpoint(request):
        print("Sensor reset requested via web")
        if reset_sensor():
            return {"status": "success", "message": "Sensor reset completed"}, 200
        else:
            return {"status": "error", "message": "Sensor reset failed"}, 500
    
    @app.route('/status')
    def status(request):
        print("GET /status - Serving status info")
        import network
        wlan = network.WLAN(network.STA_IF)
        status_info = {
            "connected": wlan.isconnected(),
            "ip": wlan.ifconfig()[0] if wlan.isconnected() else "Not connected",
            "free_memory": gc.mem_free(),
            "uptime": "Running"
        }
        return status_info, 200, {'Content-Type': 'application/json'}
    
    # ok let's get cookin'
    try:
        print("Starting web server on port 5001...")
        print("Available endpoints:")
        print("-  http://[IP]:5001/        - Current sensor data")
        print("-  http://[IP]:5001/list    - Sensor data as list")
        print("-  http://[IP]:5001/raw     - Raw sensor data")
        print("-  http://[IP]:5001/status  - System status")
        print("-  http://[IP]:5001/shutdown - Shutdown server")
        print("=" * 20)
        print("\n✓ Server is now running and ready to accept requests!")
        print("=" * 20)
        
        # give some visual cue on the pico itself
        pico_led.on()
        sleep(0.3)
        pico_led.off()
        sleep(0.3)
        pico_led.on()
        sleep(0.3)
        pico_led.off()
        sleep(1)
        
        app.run(port=5001, host='0.0.0.0')
        
    except OSError as e:
        if e.errno == 98:  # EADDRINUSE
            print("✗ Address already in use, attempting cleanup...")
            cleanup_sockets()
            sleep(2)
            print("Resetting device...")
            reset()
        elif e.errno == 12:  # ENOMEM
            print("✗ Not enough memory, collecting garbage and resetting")
            gc.collect()
            sleep(1)
            reset()
        else:
            print(f"✗ Server error: {e}")
            sleep(1)
            print("Resetting device...")
            reset()
            
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        sleep(5)
        reset()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"✗ Critical error in main: {e}")
        sleep(5)
        reset()import os
from microdot import Microdot
import network
from time import sleep
from machine import Pin, I2C, reset
import json
from picozero import pico_led
import gc

import ahtx0

ssid = 'MY_WIFI'
password = 'MY_WIFI_PASSWORD'

i2c = I2C(0, scl=Pin(17), sda=Pin(16), freq=400000)

sensor = ahtx0.AHT10(i2c)

def connect():
    """Connect to WLAN"""
    print("Starting WiFi connection...")
    pico_led.off()
    sleep(0.2)
    pico_led.on()
    sleep(0.2)
    pico_led.off()
    sleep(0.2)
    pico_led.on()
    sleep(0.2)
    pico_led.off()
    sleep(4)
    
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    sleep(0.2)
    wlan.active(True)
    sleep(0.2)
    
    attempt_i = 1
    max_attempts = 10
    
    print(f'Connecting to WiFi: {ssid}')
    wlan.connect(ssid, password)
    
    while wlan.isconnected() == False and attempt_i <= max_attempts:
        pico_led.on()
        sleep(0.5)
        pico_led.off()
        sleep(0.5)
        print(f'Waiting for connection... Attempt: {attempt_i}/{max_attempts}')
        sleep(5)
        wlan.connect(ssid, password)
        attempt_i += 1
    
    if wlan.isconnected():
        pico_led.on()
        sleep(1)
        ip = wlan.ifconfig()[0]
        print(f'✓ Connected! IP: {ip}')
        return True
    else:
        print(f'✗ Failed to connect after {max_attempts} attempts')
        return False

def get_data(gimme_raw = False):
    sleep(0.2)
    pico_led.on()
    sleep(0.2)
    pico_led.off()
    sleep(0.2)
    pico_led.on()
    sleep(0.2)
    pico_led.off()
    
    # Get them sensor readings
    temp_celsius_raw = sensor.temperature
    humidity_raw = sensor.relative_humidity
    
    # Process temperature
    if temp_celsius_raw is not None:
        temp_celsius = int(temp_celsius_raw)
        temp_farenheit = int((temp_celsius_raw * 9/5) + 32)
        temp_farenheit_raw = (temp_celsius_raw * 9/5) + 32
        print("Temperature: %f" % temp_farenheit)
    else:
        temp_celsius = temp_celsius_raw = temp_farenheit = temp_farenheit_raw = 0
    
    if humidity_raw is not None:
        humidity = int(humidity_raw)
        print("Humidity: %f %%" % humidity_raw)
    else:
        humidity = humidity_raw = 0
    
    if gimme_raw == True:
        response = {"humidity":humidity_raw,"temp_farenheit":temp_farenheit_raw, "temp_celsius":temp_celsius_raw}
    else:
        response = {"humidity":str(humidity),"temp_farenheit":str(temp_farenheit),"temp_celsius":str(temp_celsius)}
    return response

def reset_sensor():
    # Manually reset the AHTx0 sensor
    try:
        global sensor, i2c
        print("Resetting sensor...")
        sensor = ahtx0.AHT10(i2c)
        sleep(2)
        
        for i in range(3):
            temp = sensor.temperature
            hum = sensor.relative_humidity
            print(f"Readings... {i+1}: Temp={temp}°C, Humidity={hum}%")
            sleep(1)
            
        print("Sensor reset complete")
        return True
    except Exception as e:
        print(f"Sensor reset failed: {e}")
        return False

def cleanup_sockets():
    # Cleanup "stuck" sockets
    try:
        import usocket as socket
        print("Attempting socket cleanup...")
        for i in range(5):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('0.0.0.0', 5001))
                sock.close()
                print(f"Socket {i} cleaned up")
                break
            except Exception as e:
                print(f"Socket {i} cleanup failed: {e}")
                pass
    except Exception as e:
        print(f"Socket cleanup error: {e}")

def main():
    print("=" * 20)
    print("Starting Pico 2W Temperature Server")
    print("=" * 20)
    
    # garbage collect before get started
    gc.collect()
    print(f"Free memory: {gc.mem_free()} bytes")
    
    # Connect to WiFi if needed
    if not connect():
        print("WiFi connection failed, resetting...")
        sleep(5)
        reset()
        return
    
    # Initialize microdot server
    app = Microdot()
    
    @app.route('/')
    def index(request):
        print("GET / - Serving sensor data")
        response = get_data()
        return response, 200, {'Content-Type': 'application/json'}

    @app.route('/list')
    def list_data(request):
        print("GET /list - Serving sensor data as list")
        response = get_data()
        return [response], 200, {'Content-Type': 'application/json'}
    
    @app.route('/raw')
    def raw_data(request):
        print("GET /raw - Serving raw sensor data")
        response = get_data(True)
        return response, 200, {'Content-Type': 'application/json'}

    @app.get('/shutdown')
    async def shutdown(request):
        print("Shutdown requested")
        request.app.shutdown()
        return 'Server shutting down...'
    
    @app.route('/reset-sensor')
    def reset_sensor_endpoint(request):
        print("Sensor reset requested via web")
        if reset_sensor():
            return {"status": "success", "message": "Sensor reset completed"}, 200
        else:
            return {"status": "error", "message": "Sensor reset failed"}, 500
    
    @app.route('/status')
    def status(request):
        print("GET /status - Serving status info")
        import network
        wlan = network.WLAN(network.STA_IF)
        status_info = {
            "connected": wlan.isconnected(),
            "ip": wlan.ifconfig()[0] if wlan.isconnected() else "Not connected",
            "free_memory": gc.mem_free(),
            "uptime": "Running"
        }
        return status_info, 200, {'Content-Type': 'application/json'}
    
    # ok let's get cookin'
    try:
        print("Starting web server on port 5001...")
        print("Available endpoints:")
        print("-  http://[IP]:5001/        - Current sensor data")
        print("-  http://[IP]:5001/list    - Sensor data as list")
        print("-  http://[IP]:5001/raw     - Raw sensor data")
        print("-  http://[IP]:5001/status  - System status")
        print("-  http://[IP]:5001/shutdown - Shutdown server")
        print("=" * 20)
        print("\n✓ Server is now running and ready to accept requests!")
        print("=" * 20)
        
        # give some visual cue on the pico itself
        pico_led.on()
        sleep(0.3)
        pico_led.off()
        sleep(0.3)
        pico_led.on()
        sleep(0.3)
        pico_led.off()
        sleep(1)
        
        app.run(port=5001, host='0.0.0.0')
        
    except OSError as e:
        if e.errno == 98:  # EADDRINUSE
            print("✗ Address already in use, attempting cleanup...")
            cleanup_sockets()
            sleep(2)
            print("Resetting device...")
            reset()
        elif e.errno == 12:  # ENOMEM
            print("✗ Not enough memory, collecting garbage and resetting")
            gc.collect()
            sleep(1)
            reset()
        else:
            print(f"✗ Server error: {e}")
            sleep(1)
            print("Resetting device...")
            reset()
            
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        sleep(5)
        reset()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"✗ Critical error in main: {e}")
        sleep(5)
        reset()