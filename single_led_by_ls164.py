#!/usr/bin/env python

import os, sys, time
import SUNXI_GPIO as GPIO
import pdb

data_pin = GPIO.PD1
cp_pin   = GPIO.PD2
mr_pin   = GPIO.PD3

CLEAR_CHAR = -1

pins ={ data_pin: [GPIO.OUT, GPIO.LOW], 
        cp_pin:   [GPIO.OUT, GPIO.LOW], 
        mr_pin:   [GPIO.OUT, GPIO.LOW], 
      }
pin_values = [ GPIO.LOW, GPIO.HIGH ] 
led_digi_tab = [0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F ]      

"""
import sh
gpio_driver="gpio_sunxi"
def check_gpio_driver(drv_name): 
    for line in sh.lsmod(_iter = True):
        items = line.split()
        if len(items) < 2: continue
        if drv_name == items[0]: return True
    return False

def load_gpio_driver(drv_name): ## the func is not required for SUNXI_GPIO module.
    if not check_gpio_driver(drv_name):
        try:
            out = sh.modprobe(drv_name) 
            print "Success to load gpio driver: %s" % drv_name
        except Exception, e:
            print "Fail to load gpio driver!"
    else:
        print "The gpio driver has been loaded ever!"
"""

def init_pins(all_pins):
    #init module
    GPIO.init()
    for pin in all_pins:
        #configure module
        cfgs = all_pins[pin]
        GPIO.setcfg(pin, cfgs[0])
        config = GPIO.getcfg(cfgs[0])
        GPIO.output(pin, cfgs[1])
    GPIO.output(mr_pin, GPIO.HIGH)

def write_pin(pin, value):        
    global pins, pin_values
    if pin not in pins :
        print "Fail to write pin which has not been inited ever!"
        sys.exit(1)
    if value < 0 or value > len(pin_values):
        print "Fail to write pin value which is not LOW /HIGH !"
        sys.exit(1)
    GPIO.output(pin, pin_values[value]) 

def gpio_delay(timeout): ##sleep ms
    time.sleep(timeout / 1000.0) 

def send_digital_by_74ls164(digi):
    global led_digi_tab, CLEAR_CHAR
    if digi > 9 or digi < 0: 
        if digi == CLEAR_CHAR :
            led_char = 0 
        else:
            print "digit should be [0-9]!"
            sys.exit(1)
    else:
        led_char = led_digi_tab[digi]
    i = 0
    print "send digi: %d, led value: 0x%x" % (digi, led_char )
    while i < 8:
        ## clear clock  
        write_pin(cp_pin, 0) 
        ## send data to ls164
        ######write_pin(data_pin, led_char & 0x01)
        v = 1 if led_char & 0x80 != 0 else 0
        write_pin(data_pin, v ) 
        ## set clock
        #print "value : ", v 
        write_pin(cp_pin, 1) 
        i += 1
        ###led_char = led_char >> 1
        led_char = led_char << 1
        
#cleanup 
def deinit_pins(): 
    GPIO.cleanup()

def get_value_by_type(value, kt):
    try:
        if kt == None: 
           return value 
        digi = kt(value)
        return digi
    except Exception, e:
        print "Wrong value!"
        sys.exit(1)
    return None 

## format:
## key: ("value_key", value_type, default_value, has_param)
## Note: for single switch: value_type should be None
key_words={ "-b"    : ("blink", int, 0, True),
            "<int>" : ("int", int, 0, False),
          }

def get_key_word(argv):
    kv = {} 
    for k in key_words:
        vk = key_words[k][0]
        kv[vk] = key_words[k][2]
    while argv: 
        try:
            k = argv.pop(0)
            if k not in key_words:
                v = k
                k = "<int>"
            else:
                v = True
            has_param = key_words[k][3]
            if has_param:
                v = argv.pop(0) 
        except Exception, e:
            return None
        vk = key_words[k][0]
        vt = key_words[k][1]
        kv[vk] = get_value_by_type(v ,vt)
    return kv

def show_digital(argv):
    global pins
    kv = get_key_word(argv)
    if not kv : usage()
    digi = kv['int']
    blink= kv['blink']
    init_pins(pins)
    try:
        while True:
            if digi >= 0 and digi < 10:
                send_digital_by_74ls164(digi)
            if blink == 0: 
                break
            else:
                gpio_delay(blink)
                send_digital_by_74ls164(CLEAR_CHAR)
                gpio_delay(blink)
    except Exception, e:
        pass
    deinit_pins()

def clear_digital(argv):
    init_pins(pins)
    send_digital_by_74ls164(CLEAR_CHAR)
    deinit_pins()

cmd_table = { "show"  : [show_digital, 2, 4 ], 
              "clear" : [clear_digital, 1, 1 ], 
            }

def usage():
    print "led_by_ls164.py show [-b <interval>] <digital> "  
    print "led_by_ls164.py clear "  
    sys.exit(0)

if __name__ ==  "__main__" :
    argv = sys.argv 
    argc = len(argv)
    argv.pop(0)
    argc -= 1
    if argc == 0: usage()
    cmd = argv[0]
    if cmd not in cmd_table: usage()
    max_param = cmd_table[cmd][2]
    min_param = cmd_table[cmd][1]
    if argc > max_param or argc < min_param : usage()
    cmd_table[cmd][0](argv[1:])
