import os
import time
from datetime import datetime
import adafruit_ads1x15.ads1015 as ADS
import board
import busio
import pandas as pd
from adafruit_ads1x15.analog_in import AnalogIn

# 1. Αρχικοποίηση I2C και ADS1015 στη διεύθυνση 0x4B
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1015(i2c, address=0x4B)

# Ρύθμιση Gain (Εύρος τάσης: 4.096V)
ads.gain = 1

# ΣΩΣΤΗ ΡΥΘΜΙΣΗ: Ανεβάζουμε το Data Rate για να μην καθυστερεί το hardware
ads.data_rate = 3300

# Επιλογή του Pin A3 (Κανάλι 3)
chan = AnalogIn(ads, ADS.P3)

# 2. Ρυθμίσεις Δειγματοληψίας 
TARGET_SAMPLING_RATE = 333.0
SAMPLE_INTERVAL = 1.0 / TARGET_SAMPLING_RATE

print("==================================================")
print("Ξεκινάει η ΚΑΙΝΟΥΡΙΑ καταγραφή ECG...")
print("ΓΙΑ ΝΑ ΣΤΑΜΑΤΗΣΕΤΕ: Πατήστε Ctrl+C στο πληκτρολόγιο")
print("==================================================")

data_list = []
start_time = time.time()
next_sample_time = start_time

try:
    while True:
        current_time = time.time()

        # Έλεγχος ακριβείας χρόνου (Time-driven polling)
        if current_time >= next_sample_time:
            voltage = chan.voltage
            timestamp = current_time - start_time

            data_list.append({"timestamp": timestamp, "ECG": voltage})

            next_sample_time += SAMPLE_INTERVAL

            
            if len(data_list) % 1665 == 0:
                print(
                    f"Καταγράφηκαν {len(data_list)} δείγματα (~{timestamp:.0f} δευτερόλεπτα)..."
                )

except KeyboardInterrupt:
    end_time = time.time()
    duration_seconds = end_time - start_time
    print("\n\nΗ καταγραφή διακόπηκε από τον χρήστη!")
    print(
        f"Συνολική διάρκεια καταγραφής: {duration_seconds:.2f} δευτερόλεπτα."
    )

# 3. Αποθήκευση με μοναδικό όνομα βάσει Ημερομηνίας και Ώρας
if data_list:
    df = pd.DataFrame(data_list)

    folder_path = "/home/pi/Desktop/Documents/INSPiRE/Package New/Data"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    current_datetime = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"ecg_data_{current_datetime}.csv"
    output_filename = os.path.join(folder_path, file_name)

    df.to_csv(output_filename, index=False, sep=";")

    actual_fs = len(df) / duration_seconds
    print(f"Αποθηκεύτηκαν {len(df)} δείγματα στο: {output_filename}")
    print(f"Πραγματική Συχνότητα Δειγματοληψίας: {actual_fs:.2f} Hz")
else:
    print("Δεν καταγράφηκαν δεδομένα.")
