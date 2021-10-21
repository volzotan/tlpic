Device tree config file from Waveshare:
https://www.waveshare.com/wiki/CM4-IO-BASE-B

## Excerpt from the Wiki:

CSI and DSI are disabled by default. When using the camera and DSI, it will occupy three I2C devices: I2C-10, I2C-11, and I2C-0.

Open a terminal and run the following commands:
```
 sudo apt-get install p7zip-full
 wget https://www.waveshare.com/w/upload/4/41/CM4_dt_blob.7z
 7z x CM4_dt_blob.7z -O./CM4_dt_blob
 sudo chmod 777 -R CM4_dt_blob
 cd CM4_dt_blob/
```
If you want to use both cameras and DSI0
```
 sudo  dtc -I dts -O dtb -o /boot/dt-blob.bin dt-blob-disp0-double_cam.dts
```
If you want to ue both cameras and DSI1
```
sudo  dtc -I dts -O dtb -o /boot/dt-blob.bin dt-blob-disp1-double_cam.dts
```
And then connect the cameras and DSI display

1. Please power off the IO Board first before your connection.
2. Connect the power adapter after connecting the cameras and DSI display
3. Wait a few seconds before the screen boot up.
4. If the DSI LCD cannot display, please check if you have added /boot/dt-blob.bin. If there already has the dt-blob.bin, just try to reboot.
5. The camera needs to be enabled by raspi-config, enter sudo raspi-config on the terminal, choose Interfacing Options->Camera->Yes->Finish-Yes and reboot the system

### Test the Cameras:

Test camera0:

```
sudo raspivid -t 0 -cs 0
```
Test camera1:
```
sudo raspivid -t 0 -cs 1
```

Note:

HDMI1 is disabled if you use DSI interfaces for displaying, even if you just compile the corresponding files without connecting to the DSI screen, please note it.
If you want to enable the HDMI1, please remove the dt-blob.bin file with the command:
```
sudo rm -rf /boot/dt-blob.bin
```
And then turn off IO Board and reboot it. 