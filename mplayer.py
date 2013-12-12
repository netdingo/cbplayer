## encoding=utf-8
#!/usr/bin/env python
"""
cubieboard mplayer module, which plays mp3 audio.
"""
__author__    = "Dingo"
__copyright__ = "Copyright 2013, Cubieboard Player Project"
__credits__   = ["PySUNXI project"]
__license__   = "GPL"
__version__   = "0.0.2"
__maintainer__= "Dingo"
__email__     = "btrfs@sina.com"

import os, sys, time, threading
try:
    import fcntl
    import sh
except ImportError, e:
    pass
import pymp
import cbtask, ir
from   constants import *
from   led import led_format_string 
from   log import cblog
import pdb

def create_playlist(home=".",  suffix=[".mp3", ".ape", ".ogg"], **kargs):
    """
       create audio play list. parameters:
         home           : searching home
         suffix         : audio file suffix
         playlist_file  : playlist file, if None, return playlist
         get_subdirs    : True: just get subdirs, False: get files
         subdir_level   : TODO, -1: enumate all subdirs, 0: dont enter subdir, 1: enter 1-level subdir
    """
    try:
        fd = None
        playlist_file = kargs['playlist_file'] if 'playlist_file' in kargs else None
        get_subdirs   = kargs['get_subdirs'] if 'get_subdirs' in kargs else False
        subdir_level  = kargs['subdir_level'] if 'subdir_level' in kargs else -1 
        if playlist_file == None:
            play_list = []
        else:
            fd = open(os.path.join(os.getcwd(), playlist_file), 'w')
        home = os.path.abspath(home)
        level = 0
        for pathname, dirnames, filenames in os.walk(home, topdown=True):
            if get_subdirs:  
                for dir in dirnames:
                    full_path = os.path.join(home, dir)
                    ##print full_path
                    if playlist_file == None: 
                        play_list.append(full_path)
                    else:
                        print >> fd, full_path
                if level == get_subdirs: 
                    break
                level += 1
            else:
                for file in filenames:
                    prev, ext = os.path.splitext(file)
                    ext = ext.strip().lower()
                    if ext in suffix:
                        full_path = os.path.join(home, pathname, file)
                        if playlist_file == None: 
                            play_list.append(full_path)
                        else:
                            print >> fd, full_path
    except Exception, e:
        print e
    finally:
        if fd: fd.close()
        if playlist_file == None: return play_list

def exec_shell_cmd(cmd, *args):        
    try:
        exit_code = 255 
        out = None
        cmdstr = "out = sh.%s%s"%(cmd, repr(args))
        ##exec cmdstr in globals() 
        exec cmdstr
        exit_code = out.exit_code
    except sh.ErrorReturnCode_32:
        exit_code = 32
    except Exception, e:
        print e
        pass
    return exit_code

def start_rpc_bind():
    os.system('/etc/init.d/rpcbind start')
    return E_NO_ERR

def mount_media_server(srv, media_path, dest_path): 
    ## ping nfs server
    ret = E_NO_ERR
    exit_code = exec_shell_cmd('ping', "-c", "2", srv) 
    if exit_code != 0:
        msg = "Fail to connect media server: ", srv
        cblog(msg, 1)
        ret = E_FAIL_CONN_MEDIA_SRV
        return ret 
    nfs_path = "%s:%s" % (srv, media_path)  
    ## check whether mounted 
    try:
        if not os.path.exists(dest_path):
            exit_code = exec_shell_cmd('mkdir', "-p", dest_path) 
            if exit_code != 0:
                print "Fail to create dest_path ",  dest_path
                ret = E_FAIL_CREATE_DIR
                return ret 
    except Exception, e:
        pass
    try:
        out = sh.grep( sh.mount(), dest_path )
        exit_code = out.exit_code
    except Exception, e:
        exit_code = -1
        ret = E_NO_MEDIA_EXPORT
        pass
    if exit_code == 0: ## the dest_path has mounted
        return E_NO_ERR 
    ret = E_NO_ERR 
    count = 0
    while count < 2:
        exit_code = exec_shell_cmd('mount', "-t", "nfs", nfs_path, dest_path)
        if exit_code == 32: ## rpcbind did not start
            exit_code = start_rpc_bind()
            if exit_code != 0: break
            count += 1
            continue
        if exit_code != 0 and exit_code != 3: ##TODO 3 means nfs server standby  
            msg = "Fail to mount media path: ", srv
            cblog(msg, 1)
            ret = E_FAIL_MOUNT_MEDIA_SRV
        break
    return ret

def load_media_driver():
    ret = E_NO_ERR
    if not os.path.exists('/dev/mixer'):
        exit_code = exec_shell_cmd('modprobe', CUBIEBOARD_MIXER_DRV) 
        if exit_code != 0:
            msg = "Fail to load mixer driver: ", CUBIEBOARD_MIXER_DRV
            cblog(msg, 1)
            ret = E_FAIL_LOAD_MIXER_DRIVER
    return ret 
    

class MPlayerView:
    def __init__(self, player):
        self.player = player
        ## 'bg' : background message, 'fg': foreground message
        ## message format: [ timeout, message_text, blink, timer_obj, timer_id ]
        self.output = {'bg': [0, "", 0, None, None ], 
                       'fg': [0, "aud", 0, None, None ]
                      }
        self.song_timer = 0
        self.lock = threading.Lock() 
        self.old_position = 0

    def led_timeout(self, timer_id ):
        self.lock.acquire()
        v_fg = self.output['fg']
        v_bg = self.output['bg']
        if v_fg[0] > 0 and v_fg[0] < time.time(): ## time's up!
            #if v_fg[4] == timer_id:
            self.output['fg'] = list(v_bg)
            """
            duration = self.output['fg'][0] - time.time()
            if duration > 0.0 :
                new_timeout = time.time() + duration / 1000.0 
                self.start_timer(new_timeout, self.led_timeout)
            """
        self.lock.release() 

    def create_timer(self, timeout, callback):
        timer= threading.Timer(timeout, callback, [time.time()])
        return timer

    def get_output(self):
        self.lock.acquire()
        v = self.output['fg']
        showing_value = (v[1], v[2])
        self.lock.release() 
        return showing_value 

    def set_output(self, msg, **kargs):
        duration = kargs['duration'] if 'duration' in kargs else 0 
        blink    = kargs['blink'] if 'blink' in kargs else 0
        self.lock.acquire()
        if self.output['fg'][0] == 0 or duration > 0:
            slot = 'fg'
        else:
            slot = 'bg'
        if duration > 0:
            old_timer = self.output[slot][3]
            try:
                if old_timer: old_timer.cancel()
            except Exception, e:
                pass
            timeout = time.time() + duration / 1000.0 
            timer = self.create_timer(duration, self.led_timeout)
        else:
            timeout = 0 
            timer = None
        self.output[slot][0] = timeout
        self.output[slot][1] = msg
        self.output[slot][2] = blink ##TODO
        self.output[slot][3] = timer
        if timer: timer.start()
        self.lock.release() 
        #print "set_output: msg = %s, duration = %s, timeout = %s" % (msg, duration, timeout)

    def show_error(self, code):
        s = str(code)
        msg = led_format_string(str(code), "e")
        self.set_output(msg, duration = 4, blink = 3)

    def show_song_index(self, song_index, position = 0):
        if position >= 0:
            self.old_position = position
        song_idx = led_format_string(str(song_index), "s")
        self.set_output(song_idx, duration = 2, blink=3)

    def show_position(self, status, song_index, length, position):
        if status == self.player.PlayingStatus: ## pause
            song_index_str = str(song_index)
            position       = int(position /1000.0)
            pos_str        = str(position)
            str_len        = len( song_index_str ) + len(pos_str)
            if str_len <= LED_COUNT:
                ##TODO
                msg = pos_str
            else:
                ##TODO
                msg = pos_str
            self.set_output(msg)
            #print "song_index : %d, old_position: %d, position: %d" % (song_index, self.old_position, position)
            if position - self.old_position > 5:
                self.show_song_index(song_index, position)
            elif self.old_position > position:
                self.old_position = position
            else:
                pass
        pass

    def show_selected_digital(self, digit_str):
        """
            if digit_str is None, clear the LED
        """
        if digit_str:
            digit_str = "-" + digit_str
            self.set_output(digit_str, duration = 4)
        pass

    def show_exit_sign(self):
        ##TODO
        pass

    def show_stop_sign(self):
        self.set_output("stop")
        pass

    def show_pause_sign(self):
        msg = 'paus'
        self.set_output(msg, blink = 1)
        pass

    def show_song_dir(self, dir_index, blink = 0, prefix="d"):
        msg = led_format_string(str(dir_index), prefix)
        self.set_output(msg, duration = DEFAULT_LED_DURATION, blink = blink )
        pass

    def show_boot_sign(self, msg, blink = 0):
        self.set_output(msg, blink = blink)

    def show_volume(self, vol):
        msg = led_format_string(str(vol), "--")
        self.set_output(str(vol), duration = DEFAULT_LED_DURATION )

class MPlayerTask(cbtask.CbPlayerTask):
    """
        do mp3 playing, logic like below:
        1) press "left/right" key to select 'mp3' directory
        2) press 'enter' key to create play list for selected 'mp3' directory, meantime, 
           a) stop current playing
           b) remove the current play list 
        3) add file list to player 
        4) play song one by one
        5) update LED ui in time
        6) echo 'prev'/'next' key to jump previous/next song
        7) echo 'pause' key to pause song
        8) echo 'stop' key to stop playing
    """
    single_player = None 
    player_list = { }
    def __init__(self, name):
        cbtask.CbPlayerTask.__init__(self, name)
        if MPlayerTask.single_player == None:
            MPlayerTask.single_player = pymp.Player()
        self.player = MPlayerTask.single_player
        if name not in MPlayerTask.player_list:
            MPlayerTask.player_list[name] = self
        self.media_mount = False
        self.exit = False
        self.song_dirs = []
        self.song_dir_index = -1
        self.digit_select = -1
        self.digit_select_time = None
        self.viewer = MPlayerView(self.player)
        self.volume = 50 ## 50%

    def get_output(self):
        return self.viewer.get_output()

    def get_dir_list(self, dir_home):
        ## can be override
        return create_playlist(dir_home, get_subdirs = True, subdir_level = 0)

    def get_song_list(self, dir_id):
        ## can be override
        return create_playlist(dir_id)

    def stop_player(self, name):
        if name in MPlayerTask.player_list:
            task = MPlayerTask.player_list[name]
            if task.is_running():
                task.handle_exit_key()

    def main(self): ## task entry 
        global nas_srv, media_dir, local_dir 
        ret = 0 
        self.stop_player("rad")
        self.viewer.show_boot_sign("b--2")
        if not self.media_mount:
            exit_code = mount_media_server(nas_srv, media_dir, local_dir)
            if E_NO_ERR != exit_code:
                self.log("Fail to mount media server")
                self.viewer.show_error(E_NO_SONG_DIR)
                return ret 
            else:
                self.media_mount = True
        load_media_driver()                
        self.viewer.show_boot_sign("b--1")
        self.song_dirs = self.get_dir_list(local_dir)
        if len(self.song_dirs) > 0:
            self.song_dir_index = 0
        else:
            self.song_dir_index = -1 
        self.viewer.show_boot_sign("b--0", 4)
        self.test_pos = 0 
        self.test_no = 0 
        while not self.exit:
            if self.player.is_playing():
                url, status, length, position, song_index = self.player.position_update(1)
                self.viewer.show_position( status, song_index, length, position ) 
            else:
                position = 0
            self.player.check_status()
            time.sleep(1)
            self.test_no += 1
            self.test_pos = position
        ret = 0
        return ret 

    def _callback(self):
        ## TODO
        """
           will be called periodicaly.
        """
        pass

    def key_event(self, key_name):
        """
            for any key pressed, this function will be called.
        """
        if self.digit_select != -1 and self.digit_key_timeout() < 0 : ## digital key is not timeout
            if key_name not in ir.digital_key and key_name != 'enter' and key_name != 'channel_up':
                self.clear_digit_select()
        if key_name == 'enter' and self.is_running():
            self.handle_dvd_play_key()
        pass

    def handle_digital_key(self, key): ##
        """
        handle digital key(0-9), the logic likes below:
          1) when one digital key is pressed: 
            a) if previous key is also digital key, and the two key-press time interval 
               is less than KEY_MAX_INTERVAL, then combines the two digital keys into a 
               new digital.
            b) if two key-press time interval is bigger than KEY_MAX_INTERVAL, just play 
               the new selected song.
          2) when one non-digital key is pressed: 
            a) if previous key is a digital key, and the two key-press time interval is less 
               than KEY_MAX_INTERVAL, then set the digit_select to invalid
            b) if previous key is a digital key, and the two key-press time interval is bigger 
               than KEY_MAX_INTERVAL, then set play the new selected song
            c) if previous key is not a digital key, do nothing 
        """
        digit = int(key)
        self.digit_key_timeout() ## not timeout
        output = self.push_select_digit(digit)
        self.viewer.show_selected_digital(output)
        pass

    def push_select_digit(self, digit): 
        if self.digit_select == -1:
            old_v = 0
        else:
            old_v = self.digit_select 
        self.digit_select = old_v * 10 + digit
        self.digit_select_time = time.time() 
        return str(self.digit_select)

    def clear_digit_select(self):
        song_index = self.digit_select
        self.digit_select = -1
        self.digit_select_time = None
        return song_index 

    def digit_key_timeout(self, force = 0):
        """
           check and execute digit key timeout.
           force == 0: just check didit select timeout normally
           force == 1: if not timeout, return the current selectd digit value
           if return value >= 0, : digit key has times up 
                     -1          : not yet
        """
        ret = -1 
        current_time = time.time()
        if self.digit_select_time :
            idx = -1
            if current_time - self.digit_select_time >= KEY_MAX_INTERVAL : #time is up
                if force == 0: idx = self.clear_digit_select()
            elif force != 0:
                idx = self.clear_digit_select()
            ret = idx
        return ret

    def handle_exit_key(self): ##
        self.player.exit()
        self.exit = True
        self.viewer.show_exit_sign()
        pass

    def handle_enter_key(self): ##
        if self.is_running(): 
            self.handle_dvd_play_key()

    def set_volume(self, delta = 0):
        if delta != 0:
            self.volume += delta
            if self.volume < 0: 
                self.volume = 0
            elif self.volume > 100:
                self.volume = 100
        exec_shell_cmd('aumix', '-v', self.volume)

    def handle_volume_up_key(self): ## volume up            
        self.set_volume(5)            
        self.viewer.show_volume(self.volume)
        pass

    def handle_volume_down_key(self): ## volume up            
        self.set_volume(-5)            
        self.viewer.show_volume(self.volume)
        pass

    def play_song(self, song_index):
        if self.player.select_song(song_index):
            self.player.update_status("end")
            self.viewer.show_song_index(self.player.get_current_song_index())

    def play_dir(self, dir_index = -1):
        ## the previous player's status is not EndStatus, 
        ## then receate the playlist
        if dir_index >= 0:
            self.song_dir_index = dir_index
        if self.song_dir_index >= 0: 
            song_dir = self.song_dirs[self.song_dir_index]
        else:
            msg = "no songs dir found!" 
            print msg
            self.log(msg)
            self.viewer.show_error(E_NO_SONG_DIR)
            return 
        self.player.update_status("end")
        self.player.playlist_clear()
        play_list = self.get_song_list(song_dir)
        #print "add new play list: ", play_list
        self.player.playlist_add_list(play_list)
        del play_list
        play_list = None
        self.log("handle_dvd_play_key: start new list, song_dir_index: %s" % (self.song_dir_index))
        self.player.update_status("start")

    def handle_dvd_play_key(self): ##
        """
        pdb.set_trace()
        if self.player.is_playing(): 
            return
        """
        self.set_volume()
        select_idx = self.digit_key_timeout(1)
        if select_idx >=0 : 
            if select_idx < len(self.song_dirs): 
                self.play_dir(select_idx)
            else:
                return
        elif self.player.is_stopped() or self.player.is_force_end():
            self.log("handle_dvd_play_key: continue old list, song_dir_index: %s, player status: %s" % (self.song_dir_index, self.player.status))
            self.player.update_status("start")
        else:
            self.play_dir()
        self.viewer.show_song_dir(self.song_dir_index, 3)

    def handle_dvd_stop_key(self): ##
        self.player.update_status("end")
        self.viewer.show_stop_sign()
        pass

    def handle_dvd_pause_key(self): ##
        ##TODO mplayer does not support pause yet!
        #self.player.update_status("pause")
        #self.viewer.show_pause_sign()
        pass

    def handle_channel_up_key(self):
        select_idx = self.digit_key_timeout(1)
        if select_idx >=0 : 
            if select_idx < self.player.get_song_count():
                self.play_song(select_idx)
        else:
            self.handle_dvd_next_key()

    def handle_channel_down_key(self):
        select_idx = self.digit_key_timeout(1)
        if select_idx >=0 : 
            if select_idx < self.player.get_song_count():
                self.play_song(select_idx)
        else:
            self.handle_dvd_prev_key()

    def handle_dvd_prev_key(self): ## previous song
        self.log("handle_dvd_prev_key: ") 
        self.player.update_status("end")
        self.player.update_status("prev")
        self.viewer.show_song_index(self.player.get_current_song_index())
        
    def handle_dvd_next_key(self): ## next song
        self.log("handle_dvd_next_key: ") 
        self.player.update_status("end")
        self.player.update_status("next")
        self.viewer.show_song_index(self.player.get_current_song_index())

    def handle_dvd_backward_key(self): ##
        self.viewer.show_error(self.player.status)
        pass

    def handle_dvd_forward_key(self): ##
        self.viewer.show_error(int(self.test_pos / 1000.0))
        pass

    def select_song_dir(self, increment, new_value = False):
        count = len(self.song_dirs)
        if count == 0: 
            self.viewer.show_error(E_NO_SONG_DIR)
            return 
        if new_value:
            if increment < count and increment > 0:
                self.song_dir_index = increment 
            else:
                self.viewer.show_error(E_NO_SONG_DIR)
                return 
        else:
            self.song_dir_index += increment 
        self.song_dir_index = (self.song_dir_index + count ) % count 
        self.viewer.show_song_dir(self.song_dir_index)

    def handle_left_key(self): ##
        self.select_song_dir(-1)

    def handle_right_key(self): ## 
        self.select_song_dir(1)

def create_total_song_dir_list(fn):
    global nas_srv, media_dir, local_dir 
    song_dirs = create_playlist(local_dir, get_subdirs = True, subdir_level = 0)
    try:
        fd = open(fn, "wt")
        idx = 0
        for song in song_dirs:
            fd.write("%04d: " % idx)
            fd.write(song)
            fd.write("\n")
            idx += 1
        fd.close()
    except Exception, e:
        print e

if __name__ ==  "__main__" :
    argv = sys.argv
    argc = len(argv)
    if argc > 1:
        fn = argv[1]
        create_total_song_dir_list(fn)
    pass
