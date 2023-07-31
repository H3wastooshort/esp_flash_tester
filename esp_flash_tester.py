import esptool
import os.path, sys, tempfile, time, JSON

baud_rate = "115200"

if len(sys.argv) > 3:
    baud_rate = sys.argv[3]
elif len(sys.argv) < 3:
    quit("Use ith parameters [ESP Port] [Flash Size in MB] (baudrate)")

flash_size = int(sys.argv[2]) * 1024 * 1024
print("ESP on port " + sys.argv[1])
print("Flash size is %dM (%d bytes)" % (int(sys.argv[2]),flash_size))

workdir=tempfile.mkdtemp()
#taken from https://github.com/espressif/esptool/blob/fa7e37aa4c0ef0221f25c4aff45bcdca36bf146c/flasher_stub/esptool_test_stub.py
sys.path.append("..")

print("Connecting... Be sure that the ESP is in the bootloader. Maybe tie GPIO0 to GND")
cmd_con = [
        '--port', sys.argv[1],
        '--baud', baud_rate,
        '--after', 'no_reset',
        '--connect-attempts', '0',
        'flash_id'
    ]
esptool.main(cmd_con)

def match_files(fname_a,fname_b):
    file_a = open(fname_a,'rb')
    file_b = open(fname_b,'rb')
    start_idx = None
    bad_parts={}
    for idx in range (0,flash_size-1):
        if file_a.read(1) != file_b.read(1):
            if start_idx == None:
                start_idx = idx
        else:
            if start_idx != None:
                bad_parts[start_idx]=idx-start_idx
                start_idx = None
    if start_idx != None:
        bad_parts[start_idx]=flash_size-1-start_idx
    
    return bad_parts


def exec_test(file_name):
    cmd_up = [
        '--port', sys.argv[1],
        '--baud', baud_rate,
        '--after', 'no_reset',
#        '--before', 'no_reset',
        'write_flash',
        '0',
        file_name
    ]
    cmd_dn = [
        '--port', sys.argv[1],
        '--baud',baud_rate,
        '--after', 'no_reset',
#        '--before', 'no_reset',
        'read_flash',
        '0',
        str(flash_size),
        file_name+'_dl'
    ]
    print("=== Writing test data ===")
    try:
        esptool.main(cmd_up)
    except:
        pass
    time.sleep(5)
    print("=== Reading back test data ===")
    esptool.main(cmd_dn)
    
    return match_files(file_name,file_name+'_dl')
    

test_names = {
    0:"all_zero",
    1:"all_one",
    2:"alternating"
}

test_results={}

def sum_bad_parts(bad_parts):
    bp_sum = 0
    for k in bad_parts.keys():
        bp_sum += bad_parts[k]
    return bp_sum

def test_esp(t):
    test_name = test_names[t]
    print("==== Testing with "+test_name+" ====")
    file_name = os.path.join(workdir, test_name)
    test_dat_file = open(file_name,"wb")
    if t == 0:
        for b in range (0,flash_size-1):
            test_dat_file.write(b'\x00')
    elif t == 1:
        for b in range (0,flash_size-1):
            test_dat_file.write(b'\xff')
    elif t == 2:
        for b in range (0,flash_size-1):
            test_dat_file.write(b'\x55')
    test_dat_file.close()
    bad_parts = exec_test(file_name)
    print("\n==== Found %d bad parts totaling %d bytes ====\n" % (len(bad_parts.keys()), sum_bad_parts(bad_parts)))
    test_results[test_name]=bad_parts

test_esp(0)
test_esp(1)
test_esp(2)

print("\n\n")

res_print = input("Print JSON results? [y/N] ")
if res_print == "y" or res_print == "Y":
    print(test_results)

res_fn = input("Save JSON results as (leave blank to skip): ")
if len(res_fn)>0:
    res_f = open(res_fn,'w')
    res_f.write(JSON.dumps(test_results))
    res_f.close()
