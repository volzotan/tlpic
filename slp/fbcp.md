# /boot/config.txt
# set to 320x240

hdmi_group=2
hdmi_mode=87
hdmi_cvt=320 240 60 1 0 0 0
hdmi_force_hotplug=1
<!-- display_rotate=1 -->

# fbcp

# SLP revB
cmake -DSPI_BUS_CLOCK_DIVISOR=6 -DST7789VW=ON -DGPIO_TFT_RESET_PIN=20 -DGPIO_TFT_BACKLIGHT=24 -DGPIO_TFT_DATA_CONTROL=25 -DDISPLAY_CROPPED_INSTEAD_OF_SCALING=ON -DSTATISTICS=0 ..

cmake [...]
make -j

<!-- 
gpio -g mode 24 out
gpio -g write 24 0 
-->

sudo ./fbcp-ili9341
