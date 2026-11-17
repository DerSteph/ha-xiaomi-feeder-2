"""Constants for the Xiaomi Smart Pet Feeder 2 integration."""

DOMAIN = "xiaomi_feeder"
DEFAULT_NAME = "Xiaomi Smart Pet Feeder 2"
DEFAULT_SCAN_INTERVAL = 30  # seconds
FAST_SCAN_INTERVAL = 2      # seconds while dispensing
FAST_WEIGHT_SCAN_INTERVAL = 5 # seconds for bowl weight polling, only inside a fast window:
FAST_WEIGHT_LEAD_SECONDS = 120         # start this long before a scheduled meal (feeder RTC drift)
FAST_WEIGHT_MEAL_WINDOW_SECONDS = 900  # keep polling this long after a meal time / dispense
FAST_WEIGHT_IDLE_SECONDS = 300         # extend while the weight changes or a cat eats
FAST_WEIGHT_WAKE_GRAMS = 3             # weight change seen by the 30 s update that opens a window
MIN_EATING_THRESHOLD_GRAMS = 2 # minimum net grams drop to record eating session
STABILITY_REQUIRED_SAMPLES = 2 # consecutive stable samples needed to settle weight

CONF_IP = "host"
CONF_TOKEN = "token"
CONF_NAME = "name"
CONF_MAC = "mac"
CONF_MODEL = "model"
DEFAULT_MODEL = "xiaomi.feeder.iv2001"

STORAGE_KEY = "xiaomi_feeder_storage"
STORAGE_VERSION = 1

# MIoT Services, Properties, and Actions
class FeederSIID:
    DEVICE_INFO = 1
    PET_FEEDER = 2
    PHYSICAL_CONTROLS = 3
    BATTERY = 4
    CUSTOM = 5


class FeederPIID:
    # Device Info (SIID 1)
    MANUFACTURER = 1
    MODEL = 2
    SERIAL_NUMBER = 3
    FIRMWARE_REVISION = 4

    # Pet Feeder Service (SIID 2)
    DEVICE_FAULT = 1            # 0=No Faults, 1=Faults
    FOOD_LEFT_LEVEL = 6         # 0=Normal, 1=Low
    TARGET_FEEDING_MEASURE = 7   # 0-150 (portions/target)
    FEEDING_MEASURE = 8         # 0-150 (Action input)
    FOOD_STUCK_STATUS = 10      # 0=Normal, 1=Abnormal
    FOOD_OUT_STATUS = 11        # 0=Normal, 1=Abnormal
    ADD_MEAL_NOTIFY = 13        # 0=Normal, 1=Abnormal (Refill alert)
    FOOD_HEAP_STATUS = 15       # 0=No, 1=Yes (Chute heap alert)
    DAILY_EATEN_FOOD = 18       # Daily eaten food (grams)
    DAILY_BOWL_REMAINING = 20   # Daily bowl food remaining (grams)
    REALTIME_BOWL_WEIGHT = 22   # Real-time bowl scale weight (grams)
    EATEN_DIFF_PREV_DAY = 23    # Intake diff vs previous day (grams)
    FEEDER_STATUS_26 = 26       # 0=Idle, 1=Busy
    PLAN_PROGRESS_PCT = 29      # Feeding plan progress (0-100%)
    FOOD_LEVEL_DETAIL = 31      # 0=Empty, 1=Low, 2=Normal
    FEEDER_STATUS_32 = 32       # 0=Idle, 1=Busy

    # Physical Control Locked (SIID 3)
    PHYSICAL_LOCK = 1           # bool: True/False
    LOCK_MODE = 3               # 0=Off, 1=On (Screen Auto-Sleep)

    # Battery (SIID 4)
    BATTERY_LEVEL = 1           # bool / uint8

    # Custom Specification (SIID 5)
    FEEDING_PROGRAM = 1         # Hardware schedule hex string
    ADD_MEAL_STATE = 3          # Refill reminder state
    PLAN_PROGRESS_DISPLAY = 4   # Screen light-up during feeding
    FEEDING_PLAN_SWITCH = 8     # 0=Off, 1=On (Schedule Master Switch)
    ADD_MEAL_CYCLE = 10         # Refill reminder interval hours
    GRAIN_COMPENSATION = 12     # 0=Off, 1=On
    PREVENT_STACKING = 14       # 0=Off, 1=On (Anti-stacking motor rotation)
    SCHEDULE_PROGRESS = 15      # Schedule progress percentage
    DEVICE_TIMEZONE = 17        # Timezone offset in seconds (e.g. 7200)
    SCREEN_DISPLAY = 18         # 0=Left-gram, 1=Eaten-gram, 2=Percentage
    STD_OR_DST = 19             # 0=Standard, 1=DST active


class FeederAIID:
    # Pet Feeder Service (SIID 2)
    PET_FOOD_OUT = 1            # In: [Feeding Measure (PIID 8)]
    WEIGH_CALIBRATE = 2         # In: []

    # Custom Specification (SIID 5)
    FOOD_INTAKE_SETTING = 1     # In: [Food Intake Rate (PIID 5), Food Intake State (PIID 6)]
    UPDATE_FEEDING_PROGRAM = 2  # In: [Feeding Program (PIID 1)]
    ADD_MEAL_SETTING = 3        # In: [Add Meal State (PIID 3), Add Meal Cycle (PIID 10)]
    SCHEDULE_DISPLAY_SET = 4    # In: [Plan Process Display (PIID 4)]
    FOOD_INTAKE_LOW_SET = 5     # In: [Status (PIID 9)]
    ADD_MEAL_STATE_SET = 6      # In: [Status (PIID 9)]


# Screen display map
SCREEN_MODE_TO_INT = {
    "left": 0,
    "eaten": 1,
    "percentage": 2,
}

INT_TO_SCREEN_MODE = {v: k for k, v in SCREEN_MODE_TO_INT.items()}

SCREEN_DISPLAY_MAP = {
    "left-gram-display": "left",
    "eaten-gram-display": "eaten",
    "percentage-display": "percentage",
    "left": "left",
    "eaten": "eaten",
    "percentage": "percentage",
    "percent": "percentage",
    0: "left",
    1: "eaten",
    2: "percentage",
}

# Events fired on HA event bus
EVENT_FEED_COMPLETED = f"{DOMAIN}_feed_completed"
EVENT_EATING_COMPLETED = f"{DOMAIN}_eating_completed"

