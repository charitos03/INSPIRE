import time
import smbus
import collections

# Ρυθμίσεις Hardware
ADS_ADDR = 0x4b  
CHANNEL = 2      

# Ρυθμίσεις για το BPM 
THRESHOLD = 2.0  # Όταν ξεπερνάει το 1.95V θεωρούμε ότι ξεκινάει ο χτύπος
RESET_LEVEL = 1.70 # Πρέπει να πέσει κάτω από 1.7V για να περιμένει τον επόμενο

bus = smbus.SMBus(1)

# Μεταβλητές για τον υπολογισμό
beat_times = collections.deque(maxlen=5) # Μέσος όρος 5 χτύπων
last_beat_time = time.time()
waiting_for_down = False
bpm = 0

def read_ads(addr, ch):
    config = [0xE3, 0xE3]
    try:
        bus.write_i2c_block_data(addr, 0x01, config)
        time.sleep(0.01)
        data = bus.read_i2c_block_data(addr, 0x00, 2)
        val = (data[0] << 8) | data[1]
        if val > 32767: val -= 65536
        return (val >> 4) * 0.002 
    except:
        return None

print(f"--- Δοκιμή Pulse & BPM (0x4b, A2) ---")

try:
    while True:
        voltage = read_ads(ADS_ADDR, CHANNEL)
        
        if isinstance(voltage, float):
            # --- ΥΠΟΛΟΓΙΣΜΟΣ BPM ---
            if voltage > THRESHOLD and not waiting_for_down:
                now = time.time()
                duration = now - last_beat_time
                
                # Φίλτρο: Αν ο χτύπος είναι λογικός (40 - 160 BPM)
                if 0.38 < duration < 1.5:
                    instant_bpm = 60.0 / duration
                    beat_times.append(instant_bpm)
                    bpm = int(sum(beat_times) / len(beat_times))
                
                last_beat_time = now
                waiting_for_down = True
            
            # Reset για να πιάσει τον επόμενο παλμό
            if voltage < RESET_LEVEL:
                waiting_for_down = False

            # ΟΠΤΙΚΟ ΑΠΟΤΕΛΕΣΜΑ 
            bar_len = int(max(0, (voltage - 1.0) * 20)) 
            bar = "█" * bar_len
            
            # Προσθήκη BPM στην εκτύπωση
            bpm_display = f"BPM: {bpm if bpm > 0 else '--'}"
            print(f"{bpm_display} | Voltage: {voltage:.3f} V | {bar}")
            
        else:
            print(voltage)
            
        time.sleep(0.05)
        
except KeyboardInterrupt:
    print("\nΤέλος.")
