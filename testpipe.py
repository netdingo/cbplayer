import os 
import popen2
 
if __name__ == "__main__": 
    cmd ="/usr/bin/mplayer -slave -nolirc -quiet -idle -input file=/var/mplayer_input 2>/dev/null"
    pipe_in , pipe_out = popen2(cmd, "wr"); 
    for i in range(10000) 
        """
        pipe_in.write("myname"); 
        pipe_in.write("\n"); #需要换行符
        pipe_in.flush(); #需要清空缓冲区
        """
        userid = pipe_out.readline(); #读入结果
 

