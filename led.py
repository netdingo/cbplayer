## encoding=utf-8
#!/usr/bin/env python
"""
cubieboard led module, which shows simple ascii string by 4-segment led lamp.
export those following function:
"""
__author__    = "Dingo"
__copyright__ = "Copyright 2013, Cubieboard Player Project"
__credits__   = ["PySUNXI project"]
__license__   = "GPL"
__version__   = "0.0.2"
__maintainer__= "Dingo"
__email__     = "btrfs@sina.com"

import os, sys, time, threading
import socket, select
try:
    import SUNXI_GPIO as GPIO
except ImportError, e:
    pass
import pdb

COMMON_CATHODE=0
COMMON_ANODE  =1

led_mode = COMMON_ANODE

delay_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    data_pin     = GPIO.PD1
    cp_pin       = GPIO.PD2
    mr_pin       = GPIO.PD3
    led1_sel_pin = GPIO.PD4
    led2_sel_pin = GPIO.PD5
    led3_sel_pin = GPIO.PD6
    led4_sel_pin = GPIO.PD7
except Exception, e:
    pass

try:
    led_chip_selector = [led4_sel_pin, led3_sel_pin, led2_sel_pin, led1_sel_pin]
    CLEAR_CHAR = -1
    CLEAR_LED_CHAR = 0  
    LED_COUNT = len(led_chip_selector)
    pins ={ data_pin: [GPIO.OUT, GPIO.LOW], 
            cp_pin:   [GPIO.OUT, GPIO.LOW], 
            mr_pin:   [GPIO.OUT, GPIO.LOW], 
            led1_sel_pin:   [GPIO.OUT, GPIO.LOW], 
            led2_sel_pin:   [GPIO.OUT, GPIO.LOW], 
            led3_sel_pin:   [GPIO.OUT, GPIO.LOW], 
            led4_sel_pin:   [GPIO.OUT, GPIO.LOW], 
          }
    pin_values = [ GPIO.LOW, GPIO.HIGH ] 
##led_digi_tab = [0x1, 0x2, 0x4, 0x8, 0x10, 0x20, 0x40, 0x80, 0x7F, 0x6F ]     ## test single led bit
except Exception, e:
    LED_COUNT = 4
    pass

led_ascii_table = { 
'0': 0xFC , '1': 0x60 , '2': 0xDA , '3': 0xF2  , '4':  0x66 , '5': 0xB6 , 
'6': 0xBE , '7': 0xE0 , '8': 0xFE , '9': 0xF6  , '.':  0x01, 
'a': 0xFA , 'b': 0x3E , 'c': 0x1A , 'd': 0x7A  , 'e':  0xDE,  
'f': 0x8E , 'g': 0xF6 , 'h': 0x2E , 'i': 0x0C  , 'j':  0x70, 
'k': 0x0E , 'l': 0x1C , 'm': 0xF2 , 'n': 0x2A  , 'o':  0x3A, 
'p': 0xCE , 'q': 0xE6 , 'r': 0x4E , 's': 0x5A  , 't':  0x1E, 
'u': 0x38 , 'v': 0x38 , 'w': 0x00 , 'x': 0x00  , 'y':  0x4E, 
'z': 0xDA ,  
'I': 0x0C , 'C': 0x9C , 'P': 0xCE , 'U': 0x7C ,  'S':  0xB6,  
' ': 0x00 , '-': 0x02 , '_': 0x10  ,'=': 0x90 , '~': 0x80 ,
'[': 0x9C , ']': 0xF0 
}

LED_TITLE = "[==]"

if led_mode == COMMON_ANODE:
    CLEAR_LED_CHAR = 0xFF
    for ch in led_ascii_table:
        v = led_ascii_table[ch]
        led_ascii_table[ch] = (~v) & 0xFF 

def led_format_string(value, prefix=""):
    global LED_COUNT
    if not isinstance(value, str):
        value = repr(value)
    value_len = len(value)
    if value_len > LED_COUNT:
        return value[-LED_COUNT:]
    elif value_len < LED_COUNT: 
        prefix_len  = len(prefix)
        if prefix_len + value_len > LED_COUNT:
            prefix_len = 0
            prefix = ""
        space_count = LED_COUNT - value_len - prefix_len
        space = ' ' * space_count if space_count > 0 else "" 
        return  prefix + space + value
    else:
        return value

class Led:
    PIN_INITED   = False
    PIN_DEINITED = False
    def __init__(self, pins, ascii_table, led_selector):
        self.pins = pins
        self.ascii_table = ascii_table
        self.led_selector = led_selector
        if Led.PIN_INITED == False:
            self.init_pins()            
            Led.PIN_INITED = True
            Led.PIN_DEINITED = False 
        pass

    def get_led_count(self):
        return len(self.led_selector)

    def init_pins(self):
        #init module
        GPIO.init()
        for pin in self.pins:
            #configure module
            cfgs = self.pins[pin]
            GPIO.setcfg(pin, cfgs[0])
            config = GPIO.getcfg(cfgs[0])
            GPIO.output(pin, cfgs[1])
        GPIO.output(mr_pin, GPIO.HIGH)

    #cleanup 
    def deinit_pins(self): 
        if Led.PIN_INITED and Led.PIN_DEINITED == False :
            GPIO.cleanup()
            Led.PIN_INITED = False 
            Led.PIN_DEINITED = True 

    def write_pin(self, pin, value):
        global pin_values
        if pin not in self.pins :
            print "Fail to write pin which has not been inited ever!"
            sys.exit(1)
        if value < 0 or value > len(pin_values):
            print "Fail to write pin value which is not LOW /HIGH !"
            sys.exit(1)
        GPIO.output(pin, pin_values[value]) 

    def selector_led(self, chip_sel):    
        for sel in self.led_selector:
            if chip_sel == sel:
                self.write_pin(sel, 1) 
            else:
                self.write_pin(sel, 0) 

    def show_led_char(self, led_char):
        i = 0
        while i < 8:
            ## clear clock  
            self.write_pin(cp_pin, 0) 
            ## send data to ls164
            self.write_pin(data_pin, led_char & 0x01)
            ## set clock
            #print "value : ", v 
            self.write_pin(cp_pin, 1) 
            i += 1
            led_char = led_char >> 1

    def send_char_by_74ls164(self, ch, chip_sel=-1):
        global CLEAR_CHAR, CLEAR_LED_CHAR
        if ch == CLEAR_CHAR :
            led_char = CLEAR_LED_CHAR 
        elif ch not in self.ascii_table: 
            print "char should be [0-9] or [a-z.]!"
            sys.exit(1)
        else:
            led_char = self.ascii_table[ch]
        #print "send char : %d, led value: 0x%x, chip_sel: %d" % (ch, led_char, chip_sel )
        if chip_sel == -1:
            chips = self.led_selector
        elif chip_sel < len(self.led_selector):
            chips = [self.led_selector[chip_sel]]
        else:
            print "wrong led chip selector!"
            sys.exit(1)
        for sel in chips:
            GPIO.output(mr_pin, GPIO.HIGH)
            self.selector_led(sel)
            self.show_led_char(led_char)
            GPIO.output(mr_pin, GPIO.LOW)
            
class LedUI(Led, threading.Thread):
    def __init__(self, pins, ascii_table, led_selector):
        Led.__init__(self, pins, ascii_table, led_selector)
        threading.Thread.__init__(self)
        self.exit_display = False
        self.value = ""
        self.blink = 0
        pass

    def stop(self):
        self.exit_display = True

    def run(self):
        interval = 5 
        leds = self.get_led_count()
        while not self.exit_display :
            try:
                value = self.value
                blink = self.blink
                cur_time  = time.time()
                stop_time = cur_time + blink / 1000.0
                while cur_time <= stop_time:
                    sel = 0
                    while sel < leds :
                        self.send_char_by_74ls164(value[leds - sel - 1], sel)
                        sel += 1
                        self.gpio_delay(interval)  ## this is the key
                    cur_time  = time.time()
                if blink == 0 and leds < 2: 
                    break
                if blink > 0:
                    self.send_char_by_74ls164(CLEAR_CHAR)
                    self.gpio_delay(blink)
                else: ## not blink, but need to refresh the LEDs
                    self.gpio_delay(interval)
                    pass
            except Exception, e:
                print e
                pass
            ##TODO 

    def gpio_delay(self, timeout): ##sleep ms
        global delay_socket
        time.sleep(timeout / 1000.0) 
        #select.select([delay_socket], [], [], timeout / 1000.0)
        #select.select([], [], [], timeout / 1000.0)
        """
        inputs  = []
        outputs = []
        readable, writable, exceptional = select.select(inputs, outputs, inputs, timeout / 1000.0)
        """
        return True

    def led_output(self, value, blink = 0):
        self.value = led_format_string(value)
        if blink <= 9 and blink > 0: 
            blink *= 100
        self.blink = blink

def get_value_by_type(value, kt):
    try:
        if kt == None: 
           return value 
        v = kt(value)
        return v 
    except Exception, e:
        print "Wrong value!"
        sys.exit(1)
    return None 

## format:
## key: ("value_key", value_type, default_value, has_param)
## Note: for single switch: value_type should be None
key_words={ "-b"    : ("blink", int, 0, True),
            "value" : ("value", str, "", False),
            "-p"    : ("pin", int, 0, True),
            "-s"    : ("led", int, 0, True),
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
                k = "value"
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

def create_ledui_object(show_title = False): 
    led = LedUI(pins, led_ascii_table, led_chip_selector)
    title = ""
    if show_title == True:
        title = LED_TITLE 
    led.led_output(title)
    led.start()
    return led

def show(argv):
    global pins, led_ascii_table, led_chip_selector
    kv = get_key_word(argv)
    if not kv : usage()
    value = kv['value']
    blink= kv['blink']
    led = LedUI(pins, led_ascii_table, led_chip_selector)
    led.led_output(value, blink)
    led.start()
    while True:
        try:
            led.join(0.5)
        except KeyboardInterrupt, e:
            led.stop()
            break
        except Exception, e:
            led.stop()
            break
            pass
    led.join()        
    led.deinit_pins()

def show_single_led(argv):
    global pins, led_ascii_table, led_chip_selector
    kv = get_key_word(argv)
    if not kv : usage()
    ch = kv['value'][-1]
    led = kv['led']
    if led < 0 or led >= len(led_chip_selector):
        print "led serial number should be less than ", len(led_chip_selector)
        usage()
    lo = Led( pins, led_ascii_table, led_chip_selector )
    try:
        lo.send_char_by_74ls164(ch, led)
    except Exception, e:
        lo.deinit_pins()
        pass

def clear(argv):
    global pins, led_ascii_table, led_chip_selector
    led = Led( pins, led_ascii_table, led_chip_selector )
    try:
        led.send_char_by_74ls164(CLEAR_CHAR)
    except Exception, e:
        pass
    finally:
        led.deinit_pins()
        pass

def test_pin(argv):
    global pins
    kv = get_key_word(argv)
    if not kv : usage()
    value = kv['int']
    if value != 0 and value != 1: usage()
    pin   = kv['pin']
    if pin < 0 or pin > 9: usage()
    global pins, led_ascii_table, led_chip_selector
    led = Led( pins, led_ascii_table, led_chip_selector )
    pin_num = eval("GPIO.PD%s" % pin) 
    led.write_pin(pin_num, 1) 
    led.deinit_pins()

cmd_table = { "show"  : [show, 2, 4 ], 
              "clear" : [clear, 1, 1 ], 
              "led"   : [show_single_led, 4, 4 ], 
              "pin"   : [test_pin, 4, 4 ], 
            }

def usage():
    print "led.py show [-b <interval>] <value>"  
    print "   show value, can be digital, ascii string..." 
    print "   -b <interval> : specified to blink" 
    print "led.py led  -s <serial> <char> "  
    print "led.py pin <-p pin_number> <0|1> "  
    print "led.py clear "  
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

