import collections
import os

InspireStruct = collections.namedtuple('InspireStruct', 'i2c ads mpu openbci fes clock')

class HardwareStub:
    def __init__(self, addr=0, labels=None):
        self.addr = addr
        self.chan_labels = labels if labels else []
        self.channels = []
        self.obj = None

def objects(params):
    msg = []
    msg.append("Initializing Sensors Structure...")
    
    
    ads_list = [
        HardwareStub(0x48, ["Myo1", "Myo2", "Myo3", "Myo4"]),
        HardwareStub(0x49, ["Forc1", "Forc2", "Forc3", "Forc4"]),
        HardwareStub(0x4B, ["Flex1", "Flex2"])
    ]
    
    mpu_list = [
        HardwareStub(0x68, ["L_accX", "L_accY", "L_accZ"]),
        HardwareStub(0x69, ["R_accX", "R_accY", "R_accZ"])
    ]

    return InspireStruct(None, ads_list, mpu_list, HardwareStub(), None, None), msg

def activate_hardware(objects, params):
    try:
        import board
        import busio
        import adafruit_ads1x15.ads1015 as ADS
        from adafruit_ads1x15.analog_in import AnalogIn

        i2c = busio.I2C(board.SCL, board.SDA)

        for ads in objects.ads:
            try:
                real_ads = ADS.ADS1015(i2c, address=ads.addr)
                real_ads.gain = 1 
                ads.obj = real_ads
                pins = [ADS.P0, ADS.P1, ADS.P2, ADS.P3]
                ads.channels = [AnalogIn(real_ads, p) for p in pins]
            except Exception as e:
                print(f"ADS init error: {e}")

        return objects
    except:
        return objects

def data_headers(objects, pars):
    # Δυναμικό χτίσιμο των headers για το CSV (Σύνολο 18 στήλες)
    gpiodata = ["inc", "timestamp"]
    gpiodata += ["Myo1", "Myo2", "Myo3", "Myo4"]
    gpiodata += ["Forc1", "Forc2", "Forc3", "Forc4"]
    gpiodata += ["Flex1", "Flex2"]
    gpiodata += ["L_accX", "L_accY", "L_accZ", "R_accX", "R_accY", "R_accZ"]
    
    return gpiodata, []
