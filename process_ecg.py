import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt, iirnotch
import os

def filter_ecg_signal(data, fs):
    nyq = 0.5 * fs
    
    # 1. Bandpass Φίλτρο (1.0Hz έως 45Hz)
    low_cutoff = 1.0 / nyq
    high_cutoff = 45.0 / nyq
    b_bp, a_bp = butter(3, [low_cutoff, high_cutoff], btype='band')
    filtered_bp = filtfilt(b_bp, a_bp, data)
    
    # 2. Notch Φίλτρο στα 50Hz (Θόρυβος δικτύου)
    b_n, a_n = iirnotch(50.0/nyq, 30.0)
    final_filtered = filtfilt(b_n, a_n, filtered_bp)
    
    return final_filtered

def main(filename):
    try:
        # Φόρτωση δεδομένων
        df = pd.read_csv(filename, sep=';')
        
        # Υπολογισμός πραγματικής συχνότητας και διάρκειας
        total_time = df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]
        fs = len(df) / total_time
        print("==================================================")
        print(f"Ανάλυση αρχείου: {filename}")
        print(f"Συνολική Διάρκεια: {total_time:.2f} δευτερόλεπτα")
        print(f"Πραγματική Συχνότητα Δειγματισμού: {fs:.2f} Hz")
        print("==================================================")
        
        # Εφαρμογή φίλτρου
        df['ECG_Filtered'] = filter_ecg_signal(df['ECG'].values, fs)
        
        
        # Αποθήκευση των φιλτραρισμένων τιμών σε νέο CSV
        
        output_csv = filename.replace('.csv', '_filtered_data.csv')
        df.to_csv(output_csv, index=False, sep=';')
        print(f"Επιτυχία! Τα φιλτραρισμένα δεδομένα Volt αποθηκεύτηκαν στο:\n--> {output_csv}")
        print("==================================================")
        
        # Ρύθμιση λωρίδων (5 δευτερόλεπτα ανά γραμμή)
        seconds_per_strip = 5.0
        num_strips = int(np.ceil(total_time / seconds_per_strip))
        
        # Δημιουργία subplots
        fig, axes = plt.subplots(num_strips, 1, figsize=(15, 2.5 * num_strips), sharey=True)
        
        if num_strips == 1:
            axes = [axes]
            
        for i in range(num_strips):
            start_t = i * seconds_per_strip
            end_t = (i + 1) * seconds_per_strip
            
            mask = (df['timestamp'] >= start_t) & (df['timestamp'] < end_t)
            segment = df[mask]
            
            # Σχεδίαση λωρίδας
            axes[i].plot(segment['timestamp'], segment['ECG_Filtered'], color='#007acc', linewidth=1.5)
            
            axes[i].set_xlim(start_t, end_t)
            axes[i].set_ylim(-0.6, 0.6) 
            axes[i].set_ylabel('Voltage (V)', fontsize=9)
            
            # Πλέγμα στυλ καρδιογραφήματος
            axes[i].grid(True, which='both', color='gray', linestyle='--', alpha=0.4)
            axes[i].minorticks_on()
            axes[i].grid(True, which='minor', color='pink', linestyle=':', alpha=0.3)
            
            axes[i].set_title(f'Διάστημα: {start_t:.0f}s - {end_t:.0f}s', fontsize=9, loc='right', color='gray')

        axes[-1].set_xlabel('Time (Seconds)', fontsize=12)
        plt.suptitle(f'Full ECG Record (5-Second Strips) - {os.path.basename(filename)}', fontsize=14, fontweight='bold')
        
        plt.tight_layout(rect=[0, 0.03, 1, 0.96])
        
        # Αποθήκευση εικόνας
        output_img = filename.replace('.csv', '_full_strips.png')
        plt.savefig(output_img, dpi=300)
        print(f"Επιτυχία! Το πλήρες γράφημα αποθηκεύτηκε ως:\n--> {output_img}")
        print("==================================================")
        
        plt.show()
        
    except Exception as e:
        print(f"Προέκυψε σφάλμα κατά την επεξεργασία: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Χρήση: python3 process_ecg.py <όνομα_αρχείου.csv>")
    else:
        main(sys.argv[1])
