
import sys
import time
import multiprocessing
import threading # Χρειαζόμαστε και τα δύο
from datetime import datetime

# Import modules


import inspire_config
import inspire_objects
import inspire_threads
import inspire_datarecord
import inspire_interface


def main():
    # Set session variables
    participant = "stavros"
    exp_time    = datetime.now()
    scale       = True
    guide       = False
    task_type   = 1
    process     = True  
    feedback    = True
    save_data   = True

    # 1. Setup Parameters
    pars = inspire_config.params(participant, exp_time, save_data, scale, guide, process, task_type)

    # 2. Setup Objects & Headers
    objects, msg = inspire_objects.objects(pars)
    pars.session.gpio_headers, pars.session.openbci_headers = inspire_objects.data_headers(objects, pars)

    # 3. Setup Communication Queues 
    # data_queue: Μεταφέρει δεδομένα από το Recording -> Processing/Saving
    data_queue = multiprocessing.Queue()
    
    # feedback_queue: Μεταφέρει αποτελέσματα από το Processing -> Interface (GUI)
    feedback_queue = multiprocessing.Queue()
    
    # stop_event: Ένα σινιάλο για να σταματήσουν όλα τα processes ταυτόχρονα
    stop_event = multiprocessing.Event()

    # 4. Initialise Interface (Πρέπει να τρέχει στο Main Process)
    [pygame_mod, screen, pos, canvas] = inspire_interface.interface(objects, pars, msg)
    
    # Confirm
    [cont, pos] = inspire_interface.confirm(pygame_mod, screen, pars, pos)
    if not cont:
        return

    print("System Starting...")

    # ---------------------------------------------------------
    # 5. Setup Processes & Threads
    # ---------------------------------------------------------


    
    
    # Process για την Καταγραφή (Recorder)
    # Δέχεται: objects (για sensors), pars, και την ουρά εξόδου (data_queue)
    p_record = multiprocessing.Process(
        target=inspire_threads.record_task, 
        args=(objects, pars, data_queue, stop_event)
    )

    # Process για την Επεξεργασία (Processor)
    # Δέχεται: data_queue (είσοδος), feedback_queue (έξοδος για το GUI)
    p_process = multiprocessing.Process(
        target=inspire_threads.process_task, 
        args=(pars, data_queue, feedback_queue, stop_event, task_type, guide)
    )

    # B. Threads (GUI/Lightweight tasks - Πρέπει να μείνουν στο Main Process λόγω Pygame)
    
    # Thread για το Live Feedback (Interface)
    # Διαβάζει από το feedback_queue αντί για shared variables
    t_feedback = threading.Thread(
        target=inspire_threads.feedback_display_task,
        args=(pygame_mod, screen, pars, canvas, feedback_queue, stop_event)
    )

    # Thread για Monitor Display (Events του Pygame)
    t_monitor = threading.Thread(
        target=inspire_threads.monitor_display_task,
        args=(pygame_mod, stop_event)
    )

    # ---------------------------------------------------------
    # 6. Start Execution
    # ---------------------------------------------------------
    p_record.start()
    if process:
        p_process.start()
    
    t_monitor.start()
    if feedback:
        t_feedback.start()

    # ---------------------------------------------------------
    # 7. Main Loop Monitor
    # ---------------------------------------------------------
    try:
        while True:
            time.sleep(1)
            # Ελέγχουμε αν τα κρίσιμα processes είναι ζωντανά
            if not p_record.is_alive():
                print("Recording stopped unexpectedly.")
                break
            if not t_monitor.is_alive():
                print("Monitor closed.")
                break
            
            
            
    except KeyboardInterrupt:
        print("\nStopping by user request...")
    finally:
        #  Σήμα τερματισμού
        print("Stopping all processes...")
        stop_event.set()

        # Περιμένουμε να κλείσουν
        p_record.join()
        if process:
            p_process.join()
        t_monitor.join()
        if feedback:
            t_feedback.join()

        # Κλείσιμο Hardware Sessions
        if any(pars.session.openbci_headers):
             objects.openbci.stop_stream()
             objects.openbci.release_session()

        print("Finished.")
        
        # Save Logic 

# ΑΠΑΡΑΙΤΗΤΟ ΓΙΑ MULTIPROCESSING
if __name__ == '__main__':
     
    main()