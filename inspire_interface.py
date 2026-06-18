import pygame, time, queue

def map_value_to_pixels(value, val_min, val_max, px_min, px_max):
    try:
        if value < val_min: value = val_min
        if value > val_max: value = val_max
        if val_max == val_min: return 0
        norm = (value - val_min) / (val_max - val_min)
        return int(norm * (px_max - px_min))
    except:
        return 0

def interface(objects, pars, msg):
    pygame.init()
    pygame.display.set_caption(pars.config.gui_title)
    width = pars.config.gui_width
    height = pars.config.gui_height
    screen = pygame.display.set_mode((width, height), pygame.DOUBLEBUF)
    font = pygame.font.SysFont(None, pars.config.gui_fontsize)
    screen.fill(pars.config.gui_fontbgr)
    
    pos = list(pars.config.gui_startpos)
    for i in range(len(msg)):
        text = font.render(msg[i], True, pars.config.gui_fontcolor)
        screen.blit(text, pos)
        pos[1] += 25
    pygame.display.flip()

    
    labels = [
        "Myo1", "Myo2", "Myo3", "Myo4",
        "Forc1", "Forc2", "Forc3", "Forc4",
        "Flex1", "Flex2",
        "L_aX", "L_aY", "L_aZ", "R_aX", "R_aY", "R_aZ"
    ]
    return pygame, screen, pos, {'labels': labels}

def confirm(pygame, screen, pars, pos):
    font = pygame.font.SysFont(None, pars.config.gui_fontsize)
    msg = "Press Enter to begin, Esc to abort"
    text = font.render(msg, True, (255, 50, 50))
    screen.blit(text, pos)
    pygame.display.update()
    new_pos = [pos[0], pos[1] + 30]
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return False, new_pos
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: return False, new_pos
                if event.key == pygame.K_RETURN: return True, new_pos
        time.sleep(0.05)

def monitor(pygame, stop_event):
    while not stop_event.is_set():
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                stop_event.set()
                break
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    stop_event.set()
                    break
        time.sleep(0.1)
    pygame.quit()

def feedback_display(pygame, screen, pars, canvas, feedback_queue, stop_event):
    SCREEN_W, SCREEN_H = pars.config.gui_width, pars.config.gui_height
    GRAPH_Y, GRAPH_X = 150, 20
    GRAPH_H, GRAPH_W = SCREEN_H - GRAPH_Y - 80, SCREEN_W - 40
    
    labels = canvas['labels']
    num_bars = len(labels)
    bar_width = max(2, (GRAPH_W / num_bars) - 5)
    
    lbl_font = pygame.font.SysFont(None, 18)
    lbl_surfaces = [lbl_font.render(lbl, True, (255, 255, 255)) for lbl in labels]

    smoothed_values = [0.0] * num_bars
    alpha_myo = 0.25      
    alpha_slow = 0.15     
    deadzone = 0.03       
    
    
    COLOR_ATLAS = (77, 208, 225) 

    # Μεταβλητές χρονισμού για τα 30 FPS
    last_draw_time = 0.0
    fps_interval = 1.0 / 30.0  # ~0.0333 δευτερόλεπτα ανά frame

    while not stop_event.is_set():
        try:
            # Αδειάζουμε την ουρά και επεξεργαζόμαστε μαθηματικά όλα τα πακέτα 
            # για να μην δημιουργηθεί latency (καθυστέρηση στο σήμα)
            packets_read = 0
            while not feedback_queue.empty() or packets_read == 0:
                if packets_read == 0:
                    data_packet = feedback_queue.get(timeout=0.1)
                else:
                    try:
                        data_packet = feedback_queue.get_nowait()
                    except queue.Empty:
                        break
                
                packets_read += 1
                raw_values = data_packet[2:-4] # Αφαίρεση inc, ts και των 4ων Triggers
                
                # Real-time εξομάλυνση φίλτρου
                for i in range(min(len(raw_values), len(smoothed_values))):
                    current_alpha = alpha_myo if i < 4 else alpha_slow
                    diff = abs(raw_values[i] - smoothed_values[i])
                    if diff > deadzone:
                        smoothed_values[i] = (current_alpha * raw_values[i]) + ((1 - current_alpha) * smoothed_values[i])

            # Έλεγχος: Σχεδιάζουμε στην οθόνη αν έχουν περάσει 33ms από το προηγούμενο frame
            current_time = time.time()
            if current_time - last_draw_time >= fps_interval:
                last_draw_time = current_time

                # Σχεδίαση Background
                full_rect = pygame.Rect(0, GRAPH_Y, SCREEN_W, SCREEN_H - GRAPH_Y)
                pygame.draw.rect(screen, pars.config.gui_fontbgr, full_rect)
                
                graph_rect = pygame.Rect(GRAPH_X, GRAPH_Y, GRAPH_W, GRAPH_H)
                pygame.draw.rect(screen, (30, 30, 30), graph_rect)
                pygame.draw.rect(screen, (100, 100, 100), graph_rect, 1)

                Y_MIN, Y_MAX = -0.1, 5.0 

                # Σχεδίαση των Μπαρών 
                for i in range(min(len(smoothed_values), num_bars)):
                    val = smoothed_values[i]
                    px_h = map_value_to_pixels(val, Y_MIN, Y_MAX, 0, GRAPH_H)
                    
                    bx = GRAPH_X + (i * (bar_width + 5)) + 2
                    by = GRAPH_Y + GRAPH_H - px_h
                    
                    pygame.draw.rect(screen, COLOR_ATLAS, pygame.Rect(bx, by, bar_width, px_h))
                    
                    lbl_surf = lbl_surfaces[i]
                    lx = bx + (bar_width // 2) - (lbl_surf.get_width() // 2)
                    ly = GRAPH_Y + GRAPH_H + 10
                    screen.blit(lbl_surf, (lx, ly))

                pygame.display.update(full_rect)

        except queue.Empty: continue
        except Exception: break
