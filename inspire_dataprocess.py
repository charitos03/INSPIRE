import queue

def data_process(pars, data_queue, feedback_queue, stop_event, task_type, guide):
    print("Processing Thread Started (Direct Pass-Through Mode).")
    
    # Καθαρισμός τυχόν παλαιών καταλοίπων στην ουρά
    while not data_queue.empty():
        try: 
            data_queue.get_nowait()
        except: 
            break

    while not stop_event.is_set():
        try:
            # Λήψη του πακέτου των 18 στοιχείων
            new_data_point = data_queue.get(timeout=0.2)
            
            # Άμεση προώθηση στο GUI thread
            if not feedback_queue.full():
                feedback_queue.put(new_data_point)

        except queue.Empty:
            continue
        except Exception as e:
            print(f"Processing Thread Error: {e}")
            break
            
    print("Processing Thread Finished.")
