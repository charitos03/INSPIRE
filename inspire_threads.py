import inspire_interface
import inspire_datarecord
import inspire_dataprocess
import time

# --- Target Functions for Multiprocessing/Threading ---

# 1. Monitor Task (Τρέχει ως Thread στο Main Process)
def monitor_display_task(pygame, stop_event):
    """
    Διαχειρίζεται τα events του Pygame (κλείσιμο παραθύρου, κλπ).
    """
    # Περνάμε το stop_event για να ξέρει πότε να σταματήσει
    inspire_interface.monitor(pygame, stop_event)


# 2. Record Task (Τρέχει ως ξεχωριστό PROCESS)
def record_task(objects, pars, data_queue, stop_event):
    """
    Διαβάζει δεδομένα από Sensors/Teensy και τα στέλνει στην ουρά.
    """
    # Set flag inside this process memory space
    inspire_datarecord.recording = True
    
    # Καλούμε τη συνάρτηση record περνώντας την ουρά (data_queue) 
    # για να σπρώχνει τα δεδομένα προς τον Processor.
    inspire_datarecord.record(objects, pars, data_queue, stop_event)


# 3. Process Task (Τρέχει ως ξεχωριστό PROCESS)
def process_task(pars, data_queue, feedback_queue, stop_event, task_type, guide):
    """
    Τραβάει δεδομένα από το data_queue, επεξεργάζεται, και στέλνει αποτελέσματα στο feedback_queue.
    """
    inspire_dataprocess.data_process(pars, data_queue, feedback_queue, stop_event, task_type, guide)


# 4. Feedback Display Task (Τρέχει ως Thread στο Main Process)
def feedback_display_task(pygame, screen, pars, canvas, feedback_queue, stop_event):
    """
    Ενημερώνει τα γραφικά (Pygame) διαβάζοντας από το feedback_queue.
    """
    inspire_interface.feedback_display(pygame, screen, pars, canvas, feedback_queue, stop_event)

# --- Deprecated / Unused ---
# Η openbci_stream μπορεί να αφαιρεθεί αν δεν χρησιμοποιείται πλέον 
# ή να προσαρμοστεί αντίστοιχα αν την χρειαστ
