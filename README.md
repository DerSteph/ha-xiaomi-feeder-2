# Xiaomi Smart Pet Food Feeder 2 — Home Assistant Custom Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![PyPI version](https://img.shields.io/pypi/v/xiaomi-feeder-2.svg?style=for-the-badge&color=blue)](https://pypi.org/project/xiaomi-feeder-2/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg?style=for-the-badge)](LICENSE)

A high-performance, 100% local **Home Assistant Community Store (HACS)** custom integration for the **Xiaomi Smart Pet Food Feeder 2 (`xiaomi.feeder.iv2001`)**, powered by the [`xiaomi-feeder-2`](https://pypi.org/project/xiaomi-feeder-2/) library.

---

## ✨ Features

- ⚡ **100% Local MIoT Control**: Zero cloud latency, works entirely on your local Wi-Fi network.
- ⚖️ **Real-time Bowl Scale & Intake**: Live bowl food weight in grams ($g$), cumulative daily food intake, last meal intake, and tare/zero calibration.
- 🕒 **Native Settings Schedule Manager**: Decodes and flashes internal device EEPROM schedules (`HHMMPPRR`) directly from Home Assistant's native **Device Settings (Configure)** dialog.
- 🛑 **Dynamic "Skip Next Meal"**: Temporarily pause upcoming scheduled feedings (e.g. when feeding wet food or treats) and automatically restore the recurring schedule afterwards.
- 🌙 **Day/Night Screen Management**: Automated display sleep and wake triggers according to time of day or sun position.
- 🛡️ **Safety Protections**: Real-time sensors for food jams, motor stalls, dispense failures, and chute heap accumulation.
- 📊 **Native Dashboard Cards**: Out-of-the-box compatibility with Home Assistant's native Tile and Mushroom cards.

---

## 📦 Installation

### Method 1: Via HACS (Recommended)
1. Open **HACS** in your Home Assistant UI.
2. Click the three dots in the upper right corner and select **Custom repositories**.
3. Add Repository URL: `https://github.com/DerSteph/ha-xiaomi-feeder`
4. Category: **Integration**
5. Click **Add**, find **Xiaomi Smart Pet Feeder 2**, and click **Download**.
6. Restart Home Assistant.

### Method 2: Manual Installation
1. Copy the `custom_components/xiaomi_feeder` folder into your Home Assistant `<config>/custom_components/` directory.
2. Restart Home Assistant.

---

## ⚙️ Configuration

1. In Home Assistant, go to **Settings** $\rightarrow$ **Devices & Services** $\rightarrow$ **Add Integration**.
2. Search for **Xiaomi Smart Pet Feeder 2**.
3. Enter your feeder's **IP Address** and **32-character Local Device Token**.
4. Click **Submit**.

---

## 📋 Entities Provided

### 📊 Telemetry & Sensors
| Entity | Name | Description |
| :--- | :--- | :--- |
| `sensor.<device>_bowl_weight` | Bowl Food Weight | Live weight in bowl ($g$): every 10 s from 2 min before a scheduled meal until 15 min after, after dispenses and while the weight changes or after the `start_fast_polling` action; otherwise every 30 s. Attribute `fast_polling` shows the mode |
| `sensor.<device>_last_eating_session` | Last Eating Session | Grams consumed in last eating session ($g$) |
| `sensor.<device>_eating_history` | Eating History | Log of recent cat eating sessions with timestamps & durations |
| `sensor.<device>_daily_eaten_calculated`| Daily Eaten (Calculated) | Daily intake sum calculated strictly from scale weight deltas |
| `sensor.<device>_daily_eaten` | Daily Eaten Weight | Hardware-reported daily eaten counter ($g$) |
| `sensor.<device>_last_meal_intake` | Last Meal Intake | Grams consumed in last meal |
| `sensor.<device>_previous_meal_intake`| Previous Meal Intake | Grams consumed in prior meal |
| `sensor.<device>_next_feeding` | Next Feeding | Next meal timestamp & portion count |
| `sensor.<device>_schedule_count` | Schedule Meals Count | Number of EEPROM meals stored |
| `sensor.<device>_feed_history` | Feeding History | History array for timeline cards |
| `sensor.<device>_last_feed_event` | Last Feed Event | Summary of last feed event |
| `sensor.<device>_daily_progress` | Daily Plan Progress | % of today's schedule dispensed |

### 🚨 Binary Sensors & Alarms
| Entity | Name | Description |
| :--- | :--- | :--- |
| `binary_sensor.<device>_cat_eating` | Cat Eating | Active while a cat is currently at the bowl eating |
| `binary_sensor.<device>_hopper_low` | Hopper Low | Food level empty/low warning |
| `binary_sensor.<device>_food_stuck` | Food Stuck / Motor Jam | Rotor blocked alert |
| `binary_sensor.<device>_dispense_error` | Dispense Error | Dispense failure |
| `binary_sensor.<device>_food_heap` | Food Heap Detected | Food accumulation at chute |
| `binary_sensor.<device>_dispensing` | Dispensing | Active during motor rotation |
| `binary_sensor.<device>_refill_alert` | Refill Alert | Refill interval timer expired |
| `binary_sensor.<device>_fault` | Device Fault | General hardware fault |

### 🎛️ Controls, Numbers & Switches
| Entity | Type | Description |
| :--- | :--- | :--- |
| `button.<device>_feed` | Button | Dispenses manual portions |
| `button.<device>_tare_scale` | Button | Tares/calibrates bowl weight scale |
| `button.<device>_clear_schedule` | Button | Wipes device EEPROM schedule memory |
| `number.<device>_manual_portions` | Number (1–30) | Configures portions for manual feed |
| `number.<device>_target_portions` | Number (1–30) | Feeder RAM default portion setting |
| `switch.<device>_skip_next_meal` | Switch | Pauses next upcoming meal & auto-resumes |
| `select.<device>_skip_method` | Select (config) | How the meal is skipped: `remove` (default, drops it from the schedule until it has passed) or `disable_today` (the firmware's own "skipped today" flag; not honored by every feeder, and it only applies to the current day) |
| `switch.<device>_screen_auto_sleep` | Switch | Day/night display sleep mode |
| `switch.<device>_screen_progress` | Switch | Screen lights up during dispensing |
| `switch.<device>_child_lock` | Switch | Locks physical top dispenser button |
| `switch.<device>_anti_stacking` | Switch | Motor anti-accumulation reverse rotation |
| `switch.<device>_grain_compensation`| Switch | Kibble weight auto-compensation |
| `switch.<device>_schedule_enabled` | Switch | Master toggle for internal EEPROM schedule |
| `select.<device>_screen_display` | Select | Metric mode: `left`, `eaten`, `percentage` |
| `text.<device>_hardware_schedule` | Text | Hardware schedule string |

---

## 🎨 Native Dashboard Example

```yaml
type: vertical-stack
cards:
  # Row 1: Instant Feed & Portion Stepper
  - type: grid
    columns: 2
    square: false
    cards:
      - type: tile
        entity: button.xiaomi_smart_pet_feeder_2_feed
        name: Feed Cat
        icon: mdi:cat
        color: blue
        features:
          - type: button
            service: button.press
            target:
              entity_id: button.xiaomi_smart_pet_feeder_2_feed

      - type: tile
        entity: number.xiaomi_smart_pet_feeder_2_manual_feed_portions
        name: Portions
        icon: mdi:counter
        color: amber
        features:
          - type: numeric-input
            style: buttons

  # Row 2: Live Sensor Grid
  - type: grid
    columns: 2
    square: false
    cards:
      - type: tile
        entity: sensor.xiaomi_smart_pet_feeder_2_bowl_food_weight
        name: Bowl Food
        icon: mdi:scale
        color: green

      - type: tile
        entity: sensor.xiaomi_smart_pet_feeder_2_daily_eaten_weight
        name: Consumed Today
        icon: mdi:chart-timeline-variant-shimmer
        color: cyan

  # Row 3: Controls & Features
  - type: entities
    title: Controls & Features
    entities:
      - entity: switch.xiaomi_smart_pet_feeder_2_master_hardware_schedule
        name: Hardware Master Schedule
        icon: mdi:calendar-check
      - entity: switch.xiaomi_smart_pet_feeder_2_skip_next_meal
        name: Skip Next Scheduled Meal
        icon: mdi:food-drumstick-off
      - entity: switch.xiaomi_smart_pet_feeder_2_physical_child_lock
        name: Physical Button Lock
        icon: mdi:lock
      - entity: button.xiaomi_smart_pet_feeder_2_tare_scale
        name: Tare Food Bowl Scale
        icon: mdi:scale-balance
```

---

## 🛠️ Custom Services (`services.yaml`)

Every action takes an optional `device_id` (one or more feeder devices). With only one feeder set up it can be left out; with several feeders it is required, otherwise the action fails instead of guessing.

- `xiaomi_feeder.feed`: Dispenses `portions` (1–30).
- `xiaomi_feeder.calibrate_scale`: Calibrates / zeroes the bowl scale.
- `xiaomi_feeder.skip_next_meal`: Skips 1 or $N$ upcoming scheduled meal(s).
- `xiaomi_feeder.set_refill_reminder`: Configures refill alert and interval hours.
- `xiaomi_feeder.set_intake_alarm`: Configures intake alarm threshold percentage.
- `xiaomi_feeder.clear_refill_alert`: Dismisses active refill alert.
- `xiaomi_feeder.clear_intake_alert`: Dismisses active intake alert.
- `xiaomi_feeder.clear_schedule`: Wipes all EEPROM meals.
- `xiaomi_feeder.start_fast_polling`: Polls the bowl weight every 10 s for `duration` seconds (default 300) on the given `device_id`(s), e.g. when a camera sees a cat at the bowl.

---

## 📄 License
This project is licensed under the **GNU General Public License v3.0 or later (GPLv3+)**.
