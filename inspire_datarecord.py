import os, csv, time, smbus
from datetime import datetime
import inspire_objects

def record(objects, pars, data_queue, stop_event):
    # Αρχικοποίηση hardware
    inspire_objects.activate_hardware(objects, pars)

    # Headers CSV (22 στήλες)
    dynamic_headers = ["inc", "timestamp", 
                       "Myo1", "Myo2", "Myo3", "Myo4", 
                       "Forc1", "Forc2", "Forc3", "Forc4", 
                       "Flex1", "Flex2",
                       "Acc1_X", "Acc1_Y", "Acc1_Z", "Acc2_X", "Acc2_Y", "Acc2_Z",
                       "Trigger_Myo", "Trigger_Force", "Trigger_Flex", "Trigger_Acc"]

    if not os.path.exists("Data"):
        os.makedirs("Data")

    filepath = f"Data/session_backup_{int(time.time())}.csv"
    fast_bus = smbus.SMBus(1)

    def read_ads_raw(addr, channel):
        mux = {0: 0x40, 1: 0x50, 2: 0x60, 3: 0x70}
        try:
            config_high = 0x80 | mux[channel] | 0x02
            config_low = 0xE3  # 3300 SPS
            
            fast_bus.write_i2c_block_data(addr, 0x01, [config_high, config_low])
            time.sleep(0.00045)
            data = fast_bus.read_i2c_block_data(addr, 0x00, 2)
            
            val = (data[0] << 8) | data[1]
            if val > 32767: val -= 65536
            return val * 4.096 / 32768
        except:
            return 0.0

    def read_fast_mpu(addr):
        try:
            data = fast_bus.read_i2c_block_data(addr, 0x3B, 6)
            def conv(h, l):
                v = (h << 8) | l
                return (v - 65536 if v > 32767 else v) / 16384.0
            return [conv(data[0], data[1]), conv(data[2], data[3]), conv(data[4], data[5])]
        except:
            return [0.0, 0.0, 0.0]

    # Κατώφλια Ανίχνευσης Triggers
    THRES_MYO   = 0.35
    THRES_ACC   = 0.30
    THRES_FORCE = 0.35  # Προστατευτικό φράγμα για το electrical crosstalk

    CSV_ALPHA    = 0.20
    CSV_DEADZONE = 0.035

    # Buffers για triggers
    last_myo   = [0.0] * 4
    last_acc   = [0.0] * 6

    # Φιλτραρισμένες τιμές ιστορικού για το deadzone 
    flex_history  = [None, None]
    force_history = [None, None, None, None]

    # GUI Fallback Buffer
    gui_fallback = [0.0] * 12 

    # --- STATE MACHINES ---
    # Flex States (Φράγμα 0.50V - Προστασία από Shaking)
    flex_is_bent = [False, False] 
    flex_resting_voltage = [1.07, 1.07]
    state_trig_flex = 0

    # Force States (Ενεργοποιημένο για όλους τους 4 αισθητήρες)
    force_is_pressed = [False, False, False, False]
    force_resting_voltage = [2.90] * 4
    state_trig_force = 0

    # IMU States
    imu_last_trigger_time = [0.0, 0.0]
    state_trig_acc = 0

    f_csv = open(filepath, 'w', newline='')
    csv_writer = csv.writer(f_csv, delimiter=";")
    csv_writer.writerow(dynamic_headers)

    local_buffer = []
    inc = -1

    print(f"Recording started. High-Fidelity 4-Channel Force Separation Active.")

    while not stop_event.is_set():
        inc += 1
        curr_ts = datetime.now()
        current_time = time.time()

        # --- 1. MYOWARE (0x48) ---
        m1 = read_ads_raw(0x48, 0)
        m2 = read_ads_raw(0x48, 1)
        m3 = read_ads_raw(0x48, 2)
        m4 = read_ads_raw(0x48, 3)
        current_myos = [m1, m2, m3, m4]

        trig_myo = 0
        if inc > 0:
            for i in range(4):
                if abs(current_myos[i] - last_myo[i]) > THRES_MYO:
                    trig_myo += (1 << i)
        last_myo = current_myos

        # Αρχικοποίηση των "αργών" στηλών με NaN για το CSV
        forc_csv = [float('nan')] * 4
        flex_csv = [float('nan')] * 2
        acc_csv  = [float('nan')] * 6

        phase = inc % 4

        # --- 2. INTERLEAVED PHASE LOOP ---
        if phase == 0:
            # Force Sensors (0x49) - Με ενδιάμεσα micro-delays για εκμηδένιση του multiplexer ghosting
            f1 = read_ads_raw(0x49, 0)
            time.sleep(0.0002)
            f2 = read_ads_raw(0x49, 1)
            time.sleep(0.0002)
            f3 = read_ads_raw(0x49, 2)
            time.sleep(0.0002)
            f4 = read_ads_raw(0x49, 3)
            raw_forces = [f1, f2, f3, f4]

            state_trig_force = 0
            for i in range(4):
                if force_history[i] is None: force_history[i] = raw_forces[i]
                if abs(raw_forces[i] - force_history[i]) > CSV_DEADZONE:
                    force_history[i] = (CSV_ALPHA * raw_forces[i]) + ((1 - CSV_ALPHA) * force_history[i])
                gui_fallback[i] = force_history[i]
                forc_csv[i] = force_history[i]

                if inc < 12:
                    force_resting_voltage[i] = force_history[i]

            # Υπολογισμός πτώσης τάσης (drop) για κάθε αισθητήρα
            drops = [force_resting_voltage[idx] - force_history[idx] for idx in range(4)]

            # ΑΛΓΟΡΙΘΜΟΣ ΑΝΤΑΓΩΝΙΣΜΟΥ (Arbitration) ΑΝΑ ΠΕΛΜΑ
            right_active = [False, False] # Δεξί πέλμα: Forc1 & Forc2
            if max(drops[0], drops[1]) > THRES_FORCE:
                if abs(drops[0] - drops[1]) < 0.12:  # Πραγματικό ταυτόχρονο πάτημα στο βάδισμα
                    right_active[0] = drops[0] > THRES_FORCE
                    right_active[1] = drops[1] > THRES_FORCE
                else:
                    if drops[0] > drops[1]: right_active[0] = True
                    else: right_active[1] = True

            left_active = [False, False] # Αριστερό πέλμα: Forc3 & Forc4
            if max(drops[2], drops[3]) > THRES_FORCE:
                if abs(drops[2] - drops[3]) < 0.12:  # Πραγματικό ταυτόχρονο πάτημα
                    left_active[0] = drops[2] > THRES_FORCE
                    left_active[1] = drops[3] > THRES_FORCE
                else:
                    if drops[2] > drops[3]: left_active[0] = True
                    else: left_active[1] = True

            # Ενημέρωση των State Machines με βάση το φιλτραρισμένο αποτέλεσμα
            for i in range(4):
                is_active = right_active[i] if i < 2 else left_active[i-2]
                
                if not force_is_pressed[i]:
                    if inc > 12 and is_active:
                        force_is_pressed[i] = True
                else:
                    # Απελευθέρωση όταν η πίεση υποχωρήσει
                    if drops[i] <= 0.15:
                        force_is_pressed[i] = False

                if force_is_pressed[i]:
                    state_trig_force += (1 << i)

        elif phase == 1:
            # Flex 1 (0x4B, Pin A0)
            raw_f1 = read_ads_raw(0x4B, 0)
            
            if flex_history[0] is None: flex_history[0] = raw_f1
            if abs(raw_f1 - flex_history[0]) > CSV_DEADZONE:
                flex_history[0] = (CSV_ALPHA * raw_f1) + ((1 - CSV_ALPHA) * flex_history[0])
            
            gui_fallback[4] = flex_history[0]
            flex_csv[0] = flex_history[0]
            
            if inc < 12:
                flex_resting_voltage[0] = flex_history[0]
            
            if not flex_is_bent[0]:
                if inc > 12 and abs(flex_history[0] - flex_resting_voltage[0]) > 0.50:
                    flex_is_bent[0] = True
            else:
                if abs(flex_history[0] - flex_resting_voltage[0]) <= 0.15:
                    flex_is_bent[0] = False

            state_trig_flex = (1 if flex_is_bent[0] else 0) + (2 if flex_is_bent[1] else 0)

        elif phase == 2:
            # Flex 2 (0x4B, Pin A1)
            raw_f2 = read_ads_raw(0x4B, 1)
            
            if flex_history[1] is None: flex_history[1] = raw_f2
            if abs(raw_f2 - flex_history[1]) > CSV_DEADZONE:
                flex_history[1] = (CSV_ALPHA * raw_f2) + ((1 - CSV_ALPHA) * flex_history[1])
                
            gui_fallback[5] = flex_history[1]
            flex_csv[1] = flex_history[1]
            
            if inc < 12:
                flex_resting_voltage[1] = flex_history[1]
                
            if not flex_is_bent[1]:
                if inc > 12 and abs(flex_history[1] - flex_resting_voltage[1]) > 0.50:
                    flex_is_bent[1] = True
            else:
                if abs(flex_history[1] - flex_resting_voltage[1]) <= 0.15:
                    flex_is_bent[1] = False

            state_trig_flex = (1 if flex_is_bent[0] else 0) + (2 if flex_is_bent[1] else 0)

        elif phase == 3:
            # IMUs / Accelerometers
            mpu_vals = []
            if hasattr(objects, 'mpu'):
                for mpu in objects.mpu:
                    mpu_vals.extend(read_fast_mpu(mpu.addr))
            
            if len(mpu_vals) == 6:
                gui_fallback[6:] = mpu_vals
                acc_csv = mpu_vals

                if inc > 4:
                    if any(abs(gui_fallback[6+i] - last_acc[i]) > THRES_ACC for i in range(3)):
                        imu_last_trigger_time[0] = current_time
                    if any(abs(gui_fallback[6+i] - last_acc[i]) > THRES_ACC for i in range(3, 6)):
                        imu_last_trigger_time[1] = current_time
                last_acc = list(gui_fallback[6:])

            imu1_active = 1 if (current_time - imu_last_trigger_time[0] < 0.5) else 0
            imu2_active = 2 if (current_time - imu_last_trigger_time[1] < 0.5) else 0
            state_trig_acc = imu1_active + imu2_active

        # 1. Αποθήκευση στο CSV
        final_m = [inc, curr_ts, m1, m2, m3, m4] + forc_csv + flex_csv + acc_csv + [trig_myo, state_trig_force, state_trig_flex, state_trig_acc]
        local_buffer.append(final_m)

        # 2. Αποστολή στο GUI Queue
        if not data_queue.full():
            gui_packet = [inc, curr_ts, m1, m2, m3, m4] + list(gui_fallback) + [trig_myo, state_trig_force, state_trig_flex, state_trig_acc]
            data_queue.put(gui_packet)

        if len(local_buffer) >= 100:
            csv_writer.writerows(local_buffer)
            f_csv.flush()
            local_buffer.clear()

    if local_buffer:
        csv_writer.writerows(local_buffer)
    f_csv.close()
    print("Recording Stopped Clean.")
