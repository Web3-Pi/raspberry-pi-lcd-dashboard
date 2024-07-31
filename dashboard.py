"""
Author: Robert Mordzon
Organization: Web3Pi
Date: 2024-07-29
Description:
Unique hardware LCD dashboard for Raspberry Pi 4 asd Raspberry Pi 5.

This project allows you to install a color LCD display in the Argon Neo 5 case and display the following system parameters:
- CPU Usage
- CPU Temperature
- RAM Usage
- SWAP Memory Usage
- Storage Usage
- IP / Hostname
- Network Traffic (eth0/WiFi)

Hardware required:
- 1.69" LCD display with ST7789V2 Driver
  - Waveshare 24382 - [product page](https://www.waveshare.com/1.69inch-lcd-module.htm)
  or
  - Seeed Studio 104990802 - [product page](https://www.seeedstudio.com/1-69inch-240-280-Resolution-IPS-LCD-Display-Module-p-5755.html)

SPI interface must be enabled!
To do this, execute the following command and then reboot the device:
sudo sed -i '/^#dtparam=spi=on/s/^#//' /boot/firmware/config.txt
sudo reboot

License: GPL-3.0 license
Contact: robertmordzon@gmail.com

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS OR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import os
import sys
import time
import psutil
import socket
import logging
import threading
import netifaces
from lcd import LCD_1inch69
from collections import deque
from PIL import Image, ImageDraw, ImageFont

# Choose how to display CPU usage percentages
SHOW_PER_CORE = False
# False = [0 - 100%]
# True  = [0 - 400%]

# Raspberry Pi LCD pin configuration:
RST = 27
DC = 25
BL = 18
bus = 0
device = 0

# Text colors
C_BG = '#00129A' #LCD bacground
C_T1 = '#FFFFFF' #main text
C_T2 = '#c9c9c9' #text on top
C_T3 = '#c9c9c9' #text on bottom
C_W3P = ['#d5c1ee', '#e0cce4', '#c2f0ba', '#bfc7c0', '#c2cbe6', '#d5c2b7', '#b4ffe1', '#ced0e7', '#e2c9c1', '#cee8f8',
     '#e4d9d9', '#dccfc3', '#dee7f3', '#e4e9e1', '#b9c6dc', '#bdb8e3'] #colors for Web3Pi.io text

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

def main():
    logging.info('Raspberry Pi Hardware Monitor Start')
    # chceck sensors avability
    if not hasattr(psutil, "sensors_temperatures"):
        logging.error("sensors_temperatures not supported")
        sys.exit("SPI is not enabled")
    temps = psutil.sensors_temperatures()
    if not temps:
        logging.error("sensors_temperatures not supported")
        sys.exit("SPI is not enabled")

    global hostname
    hostname = get_hostname()

    # display with hardware SPI:
    disp = LCD_1inch69.LCD_1inch69()
    # Initialize library.
    disp.Init()
    # Clear display.
    disp.clear()
    # Set the backlight to 100
    disp.bl_DutyCycle(100) # ToDo: Fix hardware PWM on Rpi 5
    # If backlight is flickering a quick fix is to connect BL pin to 3.3V on Rpi to set backlight to 100%

    # https://www.fontsquirrel.com/fonts/jetbrains-mono
    Font1 = ImageFont.truetype("./font/JetBrainsMono-Medium.ttf", 35)
    Font2 = ImageFont.truetype("./font/JetBrainsMono-Medium.ttf", 25)
    Font3 = ImageFont.truetype("./font/JetBrainsMono-Medium.ttf", 20)
    Font4 = ImageFont.truetype("./font/JetBrainsMono-Medium.ttf", 15)

    # Create start image for drawing.
    image1 = Image.open('./img/splashScreen.png')
    draw = ImageDraw.Draw(image1)

    image1 = image1.rotate(0)
    disp.ShowImage(image1)

    splash_time = 5
    time.sleep(splash_time - 1) # how long to show splash image (Web3Pi logo)

    get_ip_address()

    # Create the ul/dl thread and a deque of length 1 to hold the ul/dl- values
    global transfer_rate
    transfer_rate = deque(maxlen=1)
    global net_interface
    t = threading.Thread(target=calc_ul_dl, args=(1,net_interface))

    # The program will exit if there are only daemonic threads left.
    t.daemon = True
    t.start()

    low_frequency_tasks()
    high_frequency_tasks()
    medium_frequency_tasks()

    time.sleep(1)
    try:
        # Get the current time (in seconds)
        next_time = time.time() + 1
        C_W3P_index = 0
        skip = 0
        logging.info('Entering forever loop')
        while True:
            try:
                high_frequency_tasks() # every second

                if skip % 10 == 0:
                    medium_frequency_tasks()

                if skip % 30 == 0:
                    low_frequency_tasks()


                # Draw background
                image1 = Image.open('./img/lcdbg2.png')
                draw = ImageDraw.Draw(image1)

                # Draw vertical lines
                draw.line([(240 / 3, 0), (240 / 3, (280 / 3) * 2)], fill="BLACK", width=2, joint=None)
                draw.line([((240 / 3) * 2, 0), ((240 / 3) * 2, (280 / 3) * 2  -22)], fill="BLACK", width=2, joint=None)

                # Draw horizontal lines
                draw.line([(0, 280 / 3), (240, 280 / 3)], fill="BLACK", width=2, joint=None)
                draw.line([(0, (280 / 3) * 2), (240, (280 / 3) * 2)], fill="BLACK", width=2, joint=None)
                draw.line([((240 / 3), (280 / 3) * 2 - 22), (240, (280 / 3) * 2 - 22)], fill="BLACK", width=2, joint=None)

                # CPU
                x = 0
                y = 0
                draw.text((118 + x, 108 + y), 'CPU', fill=C_T2, font=Font2, anchor="mm")
                if SHOW_PER_CORE:
                    draw.text((120 + x, 140 + y), f'{int(cpu_percent)}', fill=f'{value_to_hex_color_cpu_usage_400(int(cpu_percent))}', font=Font1, anchor="mm")
                else:
                    draw.text((120 + x, 140 + y), f'{int(cpu_percent)}', fill=f'{value_to_hex_color_cpu_usage(int(cpu_percent))}', font=Font1, anchor="mm")
                    draw.text((150 + x, 145 + y), '%', fill=C_T2, font=Font3, anchor="mm")


                # RAM
                x = 80
                y = -90
                draw.text((120 + x, 108 + y), 'RAM', fill=C_T2, font=Font2, anchor="mm")
                draw.text((120 + x, 140 + y), f'{int(mem.percent)}', fill=C_T1, font=Font1, anchor="mm")
                draw.text((145 + x, 170 + y), '%', fill=C_T2, font=Font2, anchor="mm")

                # DISK
                x = -80
                y = 0
                draw.text((120 + x, 108 + y), 'DISK', fill=C_T2, font=Font2, anchor="mm")
                draw.text((120 + x, 140 + y), f'{int(disk.percent)}%', fill=C_T1, font=Font1, anchor="mm")
                draw.text((122 + x, 170 + y), f'{disk_free_gb:.1f}GB', fill=C_T2, font=Font3, anchor="mm")

                # CPU TEMP
                x = 0
                y = -90
                draw.text((120 + x, 108 + y), 'TEMP', fill=C_T2, font=Font2, anchor="mm")
                ct = int(cpu_temp)
                draw.text((120 + x, 140 + y), f'{ct}', fill=C_T1, font=Font1, anchor="mm")
                draw.text((145 + x, 170 + y), '°C', fill=C_T2, font=Font2, anchor="mm")

                # Network
                x = -80
                y = -90
                draw.text((120 + x, 108 + y), net_interface, fill=C_T2, font=Font2, anchor="mm")
                global net_u, net_d
                if net_d >= 100:
                    draw.text((85 + x, 135 + y), f"D:{net_d:.0f}", fill=C_T1, font=Font3, anchor="lm")
                else:
                    draw.text((85 + x, 135 + y), f"D:{net_d:.1f}", fill=C_T1, font=Font3, anchor="lm")

                if net_d >= 100:
                    draw.text((85 + x, 155 + y), f"U:{net_u:.0f}", fill=C_T1, font=Font3, anchor="lm")
                else:
                    draw.text((85 + x, 155 + y), f"U:{net_u:.1f}", fill=C_T1, font=Font3, anchor="lm")

                draw.text((135 + x, 176 + y), 'Mbps', fill=C_T2, font=Font3, anchor="mm")

                # SWAP
                x = 80
                y = 0
                draw.text((115 + x, 108 + y), 'SWAP', fill=C_T2, font=Font2, anchor="mm")
                draw.text((120 + x, 140 + y), f'{int(swap.percent)}', fill=C_T1, font=Font1, anchor="mm")
                draw.text((153 + x, 145 + y), '%', fill=C_T2, font=Font2, anchor="mm")
                #draw.text((153 + x, 110 + y), '%', fill=C_T2, font=Font2, anchor="mm")

                # Local IP / HostName
                x = 40
                y = 95
                draw.text((120, 108 + y), 'IP / HOSTNAME', fill=C_T2, font=Font2, anchor="mm")
                draw.text((120, 170 + y - 35), f'{ip_local_address}', fill=C_T1, font=Font3, anchor="mm")
                draw.text((120, 170 + y - 10), f'{hostname}.local', fill=C_T1, font=Font3, anchor="mm")

                # Web3Pi.io text
                draw.text((165, 80 + y), 'Web3Pi.io', fill=C_W3P[C_W3P_index], font=Font3, anchor="mm")
                if(C_W3P_index < len(C_W3P) - 1):
                    C_W3P_index += 1
                else:
                    C_W3P_index = 0


                # Send image to lcd display
                disp.ShowImage(image1)

                skip += 1

                # Wait until the next call
                time.sleep(max(0, next_time - time.time()))
                next_time += (time.time() - next_time) // 1 * 1 + 1
            except Exception as error:
                logging.error("An exception occurred: " + type(error).__name__)
                time.sleep(1)

    except KeyboardInterrupt:
        logging.info("Loop interrupted by user")
    except Exception as error:
        logging.error("An exception occurred: " + type(error).__name__)


    logging.info('End forever loop')

    logging.info('Hardware Monitor End')

def print_stats():
    try:
        global cpu_percent, cpu_temp, disk, disk_free_gb, ip_local_address, ram, swap
        logging.info(f'Values -> CPU: {int(cpu_percent)}%, CPU_TEMP: {int(cpu_temp)}°C, RAM: {int(mem.percent)}%, SWAP: {int(swap.percent)}%, DISK: {int(disk.percent)}%')
    except Exception as error:
        logging.error("An exception occurred: " + type(error).__name__)


def get_cpu_temperature():
    """
    Retrieves the current CPU temperature using the psutil library.

    This function utilizes the `psutil.sensors_temperatures` method to fetch temperature
    sensor data from the system. If the sensors are not supported or an error occurs,
    it logs the issue and returns a default value of 0.

    Returns:
        float: The current CPU temperature in degrees Celsius. Returns 0 if sensor
               data is not available or an error occurs.

    Raises:
        KeyError: If the temperature data structure does not contain the expected keys.
                  This is caught and handled within the function.
    """
    temps = psutil.sensors_temperatures()
    if not temps:
        logging.error("w: sensors_temperatures not supported")
        return 0

    try:
        cpu_temp = temps[next(iter(temps))][0].current #cpu_thermal
    except KeyError:
        cpu_temp = 0

    #logging.info(f'CPU_TEMP= {cpu_temp} °C')

    return cpu_temp


def calc_ul_dl(dt=1, interface="eth0"):
    try:
        t0 = time.time()
        counter = psutil.net_io_counters(pernic=True)[interface]
        tot = (counter.bytes_sent, counter.bytes_recv)

        global net_u, net_d
        while True:
            last_tot = tot
            time.sleep(dt)
            counter = psutil.net_io_counters(pernic=True)[interface]
            t1 = time.time()
            tot = (counter.bytes_sent, counter.bytes_recv)
            ul, dl = [
                (now - last) / (t1 - t0) / 1000.0
                for now, last in zip(tot, last_tot)
            ]
            net_u = ul / 1024 * 8
            net_d = dl / 1024 * 8
            t0 = time.time()
    except Exception as error:
        logging.error("An exception occurred: " + type(error).__name__)


def high_frequency_tasks():
    logging.debug("high_frequency_tasks()")
    global cpu_percent
    global cpu_temp
    global SHOW_PER_CORE

    if SHOW_PER_CORE:
        cpu_percent = sum(psutil.cpu_percent(percpu=True))
    else:
        cpu_percent = psutil.cpu_percent()

    #cpu_percent = psutil.cpu_percent()

    cpu_temp = get_cpu_temperature()
    #logging.info(f'CPU_TEMP= {getCpuTemperature()} °C')



def medium_frequency_tasks():
    logging.debug("medium_frequency_tasks()")

    global mem
    global swap
    # global nvme_temp
    # global cpu_rpm
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    print_stats()

    # nvme_temp = getNvmeTemperature()
    # cpu_rpm = getCpuRpm()


def low_frequency_tasks():
    logging.debug("low_frequency_tasks()")
    global disk
    global disk_free_gb
    global ip_local_address
    global exec, node, cons
    disk = psutil.disk_usage("/")
    disk_free_gb = disk.used / (1024 ** 3)
    #disk_free_tb = disk.used / 1024 / 1024 / 1024 / 1024
    ip_local_address = get_ip_address()


def value_to_hex_color_cpu_usage(value):
    if not (0 <= value <= 100):
        return C_BG

    # Definition of Colors in RGB Format
    green = (0, 255, 0)
    yellow = (255, 255, 0)
    red = (255, 0, 0)

    if value <= 50:
        # Interpolacja między zielonym a żółtym
        ratio = value / 50
        r = int(green[0] + ratio * (yellow[0] - green[0]))
        g = int(green[1] + ratio * (yellow[1] - green[1]))
        b = int(green[2] + ratio * (yellow[2] - green[2]))
    else:
        # Interpolacja między żółtym a czerwonym
        ratio = (value - 50) / 50
        r = int(yellow[0] + ratio * (red[0] - yellow[0]))
        g = int(yellow[1] + ratio * (red[1] - yellow[1]))
        b = int(yellow[2] + ratio * (red[2] - yellow[2]))

    return f'#{r:02x}{g:02x}{b:02x}'

def value_to_hex_color_cpu_usage_400(value):
    if not (0 <= value <= 400):
        return C_BG

    # Definition of Colors in RGB Format
    green = (0, 255, 0)
    yellow = (255, 255, 0)
    red = (255, 0, 0)

    if value <= 200:
        # Interpolacja między zielonym a żółtym
        ratio = value / 200
        r = int(green[0] + ratio * (yellow[0] - green[0]))
        g = int(green[1] + ratio * (yellow[1] - green[1]))
        b = int(green[2] + ratio * (yellow[2] - green[2]))
    else:
        # Interpolacja między żółtym a czerwonym
        ratio = (value - 200) / 200
        r = int(yellow[0] + ratio * (red[0] - yellow[0]))
        g = int(yellow[1] + ratio * (red[1] - yellow[1]))
        b = int(yellow[2] + ratio * (red[2] - yellow[2]))

    return f'#{r:02x}{g:02x}{b:02x}'

def get_hostname():
    hostname = socket.gethostname()
    return hostname

def get_ip_address():
    """
    Get the local IP address, prioritizing Ethernet over WiFi.

    Returns:
        str: The local IP address or None if no IP address is found.
    """
    interfaces = ['eth0', 'wlan0']
    for interface in interfaces:
        try:
            addresses = netifaces.ifaddresses(interface)
            ip_info = addresses.get(netifaces.AF_INET)
            if ip_info:
                ip_address = ip_info[0]['addr']
                if ip_address and not ip_address.startswith("127."):
                    global net_interface
                    net_interface = interface
                    return ip_address
        except ValueError:
            continue
    return None

def is_raspberry_pi():
    """
    Checks if the script is running on a Raspberry Pi by examining the contents of /proc/cpuinfo.

    Returns:
        bool: True if running on Raspberry Pi, False otherwise.
    """
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
            if 'Raspberry Pi' in cpuinfo:
                return True
    except FileNotFoundError:
        return False
    return False

def is_spi_enabled():
    """
    Checks if SPI is enabled on Raspberry Pi by looking for SPI devices in /dev.

    Returns:
        bool: True if SPI devices are found, False otherwise.
    """
    spi_devices = ["/dev/spidev0.0", "/dev/spidev0.1", "/dev/spidev1.0", "/dev/spidev1.1"]
    for device in spi_devices:
        if os.path.exists(device):
            return True
    return False

def is_spi_enabled_config():
    """
    Checks if SPI is enabled on Raspberry Pi by reading the config.txt file.

    Returns:
        bool: True if SPI is enabled, False otherwise.
    """
    try:
        with open('/boot/firmware/config.txt', 'r') as f:
            config = f.read()
            if 'dtparam=spi=on' in config:
                return True
    except FileNotFoundError:
        return False
    return False

def check_python_version():
    """
    Checks if the current Python version is greater than 3.8.

    Returns:
        bool: True if the current Python version is greater than 3.8, False otherwise.
    """
    required_version = (3, 8)
    current_version = sys.version_info[:3]

    if current_version > required_version:
        return True
    return False


if __name__ == '__main__':
    if check_python_version():
        if is_raspberry_pi():
            if is_spi_enabled() or is_spi_enabled_config():
                main()
            else:
                logging.error("SPI is not enabled on Raspberry Pi")
                sys.exit("SPI is not enabled")
        else:
            logging.error("Only Raspberry Pi is supported")
            sys.exit("Only Raspberry Pi is supported")
    else:
        logging.error("Python version is not greater than 3.8")
        sys.exit("Python version is not greater than 3.8")
