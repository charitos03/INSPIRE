# Import modules
import os, collections, sys, serial



class InspirePars:
    def __init__(self, config, inaddr, outaddr, exp, preprocess, featextract, process, feedback, protocol, session, guide):
        self.config = config
        self.inaddr = inaddr
        self.outaddr = outaddr
        self.exp = exp
        self.preprocess = preprocess
        self.featextract = featextract
        self.process = process
        self.feedback = feedback
        self.protocol = protocol
        self.session = session
        self.guide = guide

class SessionStruct:
    def __init__(self, participant, exp_time, scale, process, task_type, gpio_headers, openbci_headers, guide):
        self.participant = participant
        self.exp_time = exp_time
        self.scale = scale
        self.process = process
        self.task_type = task_type
        self.gpio_headers = gpio_headers
        self.openbci_headers = openbci_headers
        self.guide = guide

# Τα παρακάτω είναι namedtuples (είναι σταθερά)
ConfigStruct = collections.namedtuple('ConfigStruct',
    ['sessionfolder','genpath','folderout','datafile',
     'sessionfile','original_stdout',
     'gui_title','gui_width','gui_height',
     'gui_font','gui_fontsize',
     'gui_fontbgr','gui_fontcolor','gui_startpos',
     'fig_size', 'fig_dpi', 'ylim_min', 'ylim_max'])

InAddresses = collections.namedtuple('InAddresses', 'ads_addr mpu_addr mpu_reg_addr clock_addr magn_addr magn_reg_addr eeg eeg_board_id eeg_extra_channels')
AdsAddr = collections.namedtuple('AdsAddr', 'desc vals channels')
MpuAddr = collections.namedtuple('MpuAddr', 'desc vals channels')
MpuRegAddr = collections.namedtuple('MpuRegAddr', 'desc vals')
MagnAddr = collections.namedtuple('MagnAddr', 'desc vals')
MagnRegAddr = collections.namedtuple('MagnRegAddr', 'desc vals')

OutAddresses = collections.namedtuple('OutAddresses', 'fes wheelchair')

ExpStruct = collections.namedtuple('ExpStruct',['ads_rate','ads_gain',
    'fchoice','smplrt_div','dlpfcfg',
    'fes_baudrate','fes_bytesize','fes_parity','fes_stopbits',
    'fes_timeout','fes_write_timeout','fes_xonxoff',
    'fes_rtscts','fes_dsrdtr',
    'markiv_timeout','markiv_eeg_scale','markiv_aux_scale',
    'markiv_num_samples','read_board_samples','markiv_file'])

PreprocessStruct = collections.namedtuple('PreprocessStruct', ['force_scalein','force_scaleout', 'flex_scalein','flex_scaleout'])
ProcessStruct = collections.namedtuple('ProcessStruct', ['wheelchair_states','gait_states','thresholds_gait','thresholds_eeg','thresholds_emg','fes_current','fes_pulse_width','channel_mode'])
ProtocolStruct = collections.namedtuple('ProtocolStruct', ['stimuli'])

#################################################

# Call functions to define all parameters
def params(participant,exp_time,save_data,scale,guide,process,task_type):
    
    config_obj = config_params(participant)
    inaddr_obj = i2c_addr_in()
    outaddr_obj = out_addr()
    exp_obj = exp_params()
    preprocess_obj = preprocess_params()
    process_obj = process_params()
    feedback_obj = feedback_params()
    protocol_obj = protocol_stimuli(task_type)
    
    # Create Session Object (Using Class)
    task_str = 'walking' if task_type == 1 else 'wheelchair'
    # gpio_headers και openbci_headers αρχικοποιούνται κενά []
    session_obj = SessionStruct(participant, exp_time, scale, process, task_str, [], [], guide)
    
    # Create Main Object (Using Class)
    inspire_pars = InspirePars(config_obj, inaddr_obj, outaddr_obj, exp_obj, 
                               preprocess_obj, None, process_obj, feedback_obj, 
                               protocol_obj, session_obj, guide)
    
    return inspire_pars

#################################################

def config_params(participant):
    
    config_original_stdout = None
    
    # Windows-safe paths
    config_genpath = "Data" 
    config_subjectfolder = os.path.join(config_genpath, participant)
    
    gpiodatafile = "gpiorecordings.csv" 
    openbcidatafile = "openbcirecordings.csv" 
    sessionfile = "sessiondata.csv" 
    logfile = "logfile.txt" 
    
    sessionfolder, gpiofile, openbcifile, sessfile, logf = \
        output_dirs(config_genpath, config_subjectfolder, gpiodatafile, openbcidatafile, sessionfile, logfile)
    
    # Interfacing
    # Use 'arial.ttf' or None for Windows
    return ConfigStruct(sessionfolder, config_genpath, None, None, sessfile, config_original_stdout,
                        "INSPiRE", 800, 500, 'arial.ttf', 15, [0, 0, 0], [255, 255, 255], [10,10],
                        [4, 4], 60, -0.2, 3.5)

#################################################

def output_dirs(genpath, subjectfolder, gpiodatafile, openbcidatafile, sessionfile, logfile):
    if not os.path.exists(genpath):
        os.mkdir(genpath)
    if not os.path.exists(subjectfolder): 
        os.mkdir(subjectfolder)
        
    folders = os.listdir(subjectfolder)
    existing_folders = len([s for s in folders if "session" in s])
    sessionfolder = os.path.join(subjectfolder, "session" + str(existing_folders+1))
    os.mkdir(sessionfolder)
    
    return sessionfolder, os.path.join(sessionfolder, gpiodatafile), os.path.join(sessionfolder, openbcidatafile), os.path.join(sessionfolder, sessionfile), os.path.join(sessionfolder, logfile)

#################################################

def i2c_addr_in():
    
    # ADS
    ads_desc = ["ADS1: 4 Myoware sensors", "ADS2: 4 Pressure sensors", "ADS3: 2 ECG & 2 Flex sensors", "ADS4: FES input channels"]
    ads_vals = [0x48, 0x49, 0x4b, 0x4a]
    ads_chans = [["Myoware 1", "Myoware 2", "Myoware 3", "Myoware 4"],
                 ["Force_Toe_R","Force_Heel_R","Force_Toe_L","Force_Heel_L"],
                 ["Flex_Knee_R","Flex_Knee_L","Pulse","ECG"],
                 ["FES_1_R","FES_2_R","FES_1_L","FES_2_L"]]
    ads_obj = AdsAddr(ads_desc, ads_vals, ads_chans)
    
    # MPU
    mpu_desc = ["IMU1: Right Leg", "IMU2: Left Leg"]
    mpu_chans = [["R_acc_x","R_acc_y","R_acc_z"], ["L_acc_x","L_acc_y","L_acc_z"]]
    mpu_vals = [0x68, 0X69]
    mpu_obj = MpuAddr(mpu_desc, mpu_vals, mpu_chans)
    
    mpu_reg_desc = ["TEST_GYRO_X","TEST_GYRO_Y","TEST_GYRO_Z","TEST_ACC_X","TEST_ACC_Y","TEST_ACC_Z","SMPLRT_DIV","CONFIG","PWR_MGMT_1","GYRO_CONFIG","ACC_CONFIG","ACC_CONFIG2","WOM_THR","FIFO_EN","INT_ENABLE","ACCEL_XOUT_H","ACCEL_XOUT_L","ACCEL_YOUT_H","ACCEL_YOUT_L","ACCEL_ZOUT_H","ACCEL_ZOUT_L","TEMP_OUT_H","TEMP_OUT_L","GYRO_XOUT_H","GYRO_XOUT_L","GYRO_YOUT_H","GYRO_YOUT_L","GYRO_ZOUT_H","GYRO_ZOUT_L"]
    mpu_reg_vals = [0x00,0x01,0x02,0x0D,0x0E,0x0F,0x19,0x1A,0x6B,0x1B,0x1C,0x1D,0x1F,0x23,0x38,0x3B,0x3C,0x3D,0x3E,0x3F,0x40,0x41,0x42,0x43,0x44,0x45,0x46,0x47,0x48]
    mpu_reg_obj = MpuRegAddr(mpu_reg_desc, mpu_reg_vals)
    
    # Magnetometer
    magn_obj = MagnAddr(["AK8963"], [0x0C])
    magn_reg_obj = MagnRegAddr(["AK8963_ST1","AK8963_ST2","AK8963_CNTL","ASTC","HXL","HXH","HYL","HYH","HZL","HZH"], [0x02,0x09,0x0A,0x0C,0x03,0x04,0x05,0x06,0x07,0x08])
    
    eeg = '/dev/ttyUSB1'
    eeg_board_id = 2
    eeg_extra = ["Accel_x","Accel_y","Accel_z"] + ["Unknown","D11_dig","D12_dig","D13_dig","D12_anmode","D17","D18", "D11_ana","D12_ana","D13_ana"] + ["timestamp","marker"]
    
    return InAddresses(ads_obj, mpu_obj, mpu_reg_obj, None, magn_obj, magn_reg_obj, eeg, eeg_board_id, eeg_extra)

#################################################

def out_addr():
    return OutAddresses("/dev/ttyUSB0", "")

#################################################

def exp_params():
    # ADS
    ads_rate = 3300
    ads_gain = 2
    
    # MPU
    fchoice = 2
    smplrt_div = 0
    
    # OpenBCI
    markiv_timeout = 4
    markiv_eeg_scale = (4500000)/24/(2**23-1)
    markiv_aux_scale = 0.002 / (2**4)
    markiv_num_samples = 45000
    read_board_samples = 1
    
    # FES
    fes_baudrate=115200
    fes_bytesize=serial.EIGHTBITS
    fes_parity="N"
    fes_stopbits=serial.STOPBITS_ONE
    fes_timeout=0
    fes_write_timeout=None
    fes_xonxoff=False
    fes_rtscts=False
    fes_dsrdtr=False
    
    return ExpStruct(ads_rate, ads_gain, fchoice, smplrt_div, None,
                     fes_baudrate, fes_bytesize, fes_parity, fes_stopbits,
                     fes_timeout, fes_write_timeout, fes_xonxoff, fes_rtscts, fes_dsrdtr,
                     markiv_timeout, markiv_eeg_scale, markiv_aux_scale,
                     markiv_num_samples, read_board_samples, '')

#################################################

def preprocess_params():
    return PreprocessStruct([1.2,2.2], [0,3], [0.7,1.1], [0,2])

#################################################

def feature_params():
    return None

#################################################

def process_params():
    wheelchair_states = ['Forward', 'Backward', 'Right', 'Left', 'Stop']
    gait_states = ['stance','midstance_l','heelstrike_r','toeoff_l','midstance_r','heelstrike_l','toeoff_r']
    
    
    thresholds_gait = [1.8, 1.8, 1, 1, 1]
    thresholds_eeg = [1, 1, 1, 1, 1]
    thresholds_emg = [1, 1, 1, 1]

    print(f"DEBUG: EMG Thresholds length is: {len(thresholds_emg)}")
    
    
    return ProcessStruct(wheelchair_states, gait_states, thresholds_gait, thresholds_eeg, thresholds_emg, 120, 200, 3)

def feedback_params():
    return None

def protocol_stimuli(task_type):
    if task_type == 1:
        stimuli = [['Real right step', 'Real left step', 'Real 4 steps'],
                   ['Imaginary right step', 'Imaginary left step', 'Imaginary 4 steps']]
    else:
        stimuli = [['Stop','Forward','Backward','Right','Left']]
    
    return ProtocolStruct(stimuli)