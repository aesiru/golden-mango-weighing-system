# Hackathon — IoT Weight Display

ESP32-C5 sketch with I2C LCD, MQTT, and button controls.

## Pin Wiring (ESP32-C5-DevKitC-1)

| Peripheral | GPIO | Header Pin | Label     |
|------------|------|------------|-----------|
| I2C SDA    | 2    | J1 pin 3   | LP_I2C_SDA |
| I2C SCL    | 3    | J1 pin 4   | LP_I2C_SCL |
| Button 1   | 0    | —          | Publish weight |
| Button 2   | 4    | J3 pin 8   | Switch back to weight |

## Gotchas

### LP_I2C may need explicit frequency

The C5 uses the **LP_I2C** (low-power I2C) peripheral on GPIO2/3, not the regular I2C controller found on classic ESP32s. If the LCD fails to initialise (blank screen, no backlight response), try passing the clock frequency explicitly:

```cpp
// In setup(), replace:
Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);

// With:
Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN, 100000);  // 100 kHz standard mode
```

### LCD address may be 0x3F

If the LCD shows nothing, your backpack may use `0x3F` (PCF8574A) instead of `0x27` (PCF8574). Change `LCD_I2C_ADDR` at the top of the sketch, or run an I2C scanner to check.
