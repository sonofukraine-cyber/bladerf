from bladerf import BladeRF
# Initialize the BladeRF device
device = BladeRF()
# Retrieve and print device information
print(f"Device Name: {device.board_name}")
print(f"Serial Number: {device.serial}")
print(f"FPGA Version: {device.fpga_version}")
print(f"Firmware Version: {device.fw_version}")
# Close the device after use
device.close()