# Mordomus Gen1 (PCCWd) Home Assistant Bridge

The purpose of this software is to be able to control the various modules connected to the **Mordomus gen1 (PCCWd) module**, for integration with applications such as home assistant, as opposed to having to use the proprietary application

## Supported Hardware


* **Main Gateway:** `PCCWd` module
* **Blinds:** `WINW3d` module
* **Outputs:** `OF4Wd`/`OF8Wd` module
* **Inputs:** `IN4Wd`/`IN10Wd`/`IN22Wd` module

## Prerequisites

### Required
* **MQTT Broker:** Running and communicating with Home Assistant (e.g., Mosquitto).
* **[Waveshare RS232-to-Ethernet Converter](https://www.waveshare.com/wiki/RS232_TO_ETH_(B)):** Connected to the serial port of the PCCWd module (**TX**, **RX**, and **GND**) according to its setup guide.
* **Module Function IDs:** Knowing the IDs for each input and output device.

### Optional
* **Input Function Mappings (`mods_input_func`):** Mapping button actions to output targets. This is necessary to keep light states synchronized in Home Assistant when physical wall buttons are pressed.

## Automated Configuration Utility

If you have access to the official Mordomus software, you can automatically generate your complete configuration file:

1. Locate the official database files:
   * `mods_input.DB`
   * `mods_output.DB`
   * `mods_input_func.DB`
2. Open them using a Paradox DB viewer, such as [MiTeC Paradox Data Editor](https://www.mitec.cz/wp/mpde/).
3. Export each file as a **CSV with a semicolon (`;`) delimiter**.
4. Move the exported CSV files into the `helper/` directory.
5. Run the helper script to interactively generate your `config.yaml` (which will also prompt for your MQTT and Waveshare settings):
   ```bash
   python helper/main.py

## Manual Configuration

If you do not have access to the official software or exported database files, you can discover your hardware IDs manually by monitoring or sending raw serial telemetry:

### 1. Serial Connection
Connect directly to the PCCWd module using an RS-232 cable or via your Waveshare bridge configured with the following serial parameters:
* **Baud Rate:** `14400`
* **Data Bits:** `8`
* **Parity:** `None`
* **Stop Bits:** `1`

---

### 2. Discovering Outputs (Lights & Blinds)
To find output IDs, send test commands in hex format:
```hex
0xAA [DEVICE_ID] 0x64
```
* Increment `[DEVICE_ID]` (e.g., `0x01`, `0x02`, `0x03`...) until a light or a blind move (it's the same command for both)
* Take note of the ID corresponding to each physical device.
* There are also two helpful ways to make it easier, you can also send a 0x68 as opposed to 0x64, which will flash the correspondent light 5 times, and pair that with listening to the noises the relays in your modules make, because if theres no relay noise when you turn something on or off, then there probably isn't anything tied to that ID.

---

### 3. Discovering Inputs (Wall Buttons)
To find input IDs, monitor the serial stream while physically pressing wall buttons. When pressed, the module will broadcast a packet in this format:
```hex
0x49 0xAA [INPUT_ID] [CLICK_TYPE] 0x46
```
* **`[INPUT_ID]`**: ID of the pressed wall switch.
* **`[CLICK_TYPE]`**: The type of click detected (`Single Click`, `Double Click`, or `Continuous Click`).

---

### 4. Updating Configuration
Once all required IDs are mapped out, create a `config.yaml` file (you can copy `config.example.yaml`) and enter manually enter the IDs and respective names.


## Known Issues
 * Blinds status on HA will not be in sync with what's actaully happening, this is due to my installation having the blinds wall switches directly connected to them, therefore bypassing the module, which means i can't have the switches "talk" with the rest of the system, and I still haven't found a way to ask the PCCWd for the status of a given input/output, so as of now there isn't a fix.
 * Modules not listed, I can't test/add any modules that aren't listed, as I don't have them, but feel free to modify the program for your own needs.

## Disclaimer

This project is an independent, open-source integration developed for personal use and interoperability. It is **not** affiliated with Mordomus. All product and company names are trademarks™ or registered® trademarks of their respective holders. Use of them does not imply any affiliation with or endorsement by them.