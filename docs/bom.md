# Bill of materials

Product names and basic specs only - no purchase links, since links expire.

## Gate node (at the pole)

- Electromagnetic lock, holding-type (not a latch) - fail-safe, power loss = unlocked
- RFID reader module RC522 (MFRC522, 13.56MHz) + 6x tags/keyfobs (13.56MHz)
- ESP32 dev board
- INMP441 I2S MEMS microphone (24-bit)
- MAX98357 I2S Class-D amplifier module (3W, DAC)
- Mini speaker, 40mm, 3W, 4 ohm
- Vandal-resistant push button (outdoor)
- Relay module (switches the electromagnet from the 12VDC rail)
- Step-down (buck) converter, 12V to 5V, for the ESP32

## House node (indoors)

- ESP32 dev board
- INMP441 I2S MEMS microphone (24-bit)
- MAX98357 I2S Class-D amplifier module (3W, DAC)
- Mini speaker, 40mm, 3W, 4 ohm
- Vandal-resistant push button (indoor)
- Powered separately from a wall outlet (see `power.md`)

## Shared / infrastructure

- PSU: "Zasilacz LED 12V 36W" - waterproof/hermetic, IP67, narrow form factor
- 20m power cable (mains run from the house PSU to the gate, through existing buried conduit)
- PETG filament (enclosure printing - chosen over PLA for outdoor durability)
- Kaiden C 3D printer (for enclosures)

See `power.md` for the power chain and `workflow.md` for how this project is branched/documented.
