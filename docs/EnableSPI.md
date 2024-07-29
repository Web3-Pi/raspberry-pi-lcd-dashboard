# Enable SPI Interface

* Open the terminal, use the command to enter the configuration page:

```
sudo apt-get install raspi-config
sudo raspi-config
```

Choose Interfacing Options -> SPI -> Yes  to enable SPI interface

![RPI_open_spi_1.png](img/RPI_open_spi_1.png)

Reboot Raspberry Pi：

```
sudo reboot
```

* Check /boot/config.txt and you can see that 'dtparam=spi=on' has been written.

![Raspberry_Pi_SPI_config.jpg](img/Raspberry_Pi_SPI_config.jpg)

* To make sure that the SPI is not occupied, it is recommended that other driver overrides be turned off for now. You can use ls /dev/spi* to check the SPI occupancy. The terminal output /dev/spidev0.0 and /dev/spidev0.1 indicates that the SPI status is normal.

![Raspberry_Pi_SPI_test.jpg](img/Raspberry_Pi_SPI_test.jpg)