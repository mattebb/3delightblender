
import socketserver
import struct
import bpy
import time

class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer): pass

class MyTCPHandler(socketserver.BaseRequestHandler):
    """
    The RequestHandler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """
    got_setup = False
    

    def handle(self):
        image_data = 104
        image_end = 105

        # self.request is the TCP socket connected to the client
        print('doing setup')
        self.data = self.request.recv(1024)
        data = self.data.split(b";")
        #0 is image name
        image_name = data[0].decode('utf-8')[1:]
        print(image_name)
        #then dspy params
        dspy_params = data[1]
        print(dspy_params)
        
        self.data = data[2]
        #we need 36 bytes here
        if len(self.data) < 33: 
            self.data += self.request.recv(36)
        xmin, xmax, ymin, ymax, a_len, z_len, channel_len, num_channels, merge = struct.unpack("!IIIIIIIIb", self.data[1:])
        print(xmin, xmax, ymin, ymax)
        print(a_len, z_len, channel_len, num_channels)
        pixel_size = int(a_len/8) + int(z_len/8) + int(channel_len/8 * num_channels) #bits ->bytes
        num_channels = num_channels + 1 if a_len > 0 else num_channels
        num_channels = num_channels + 1 if z_len > 0 else num_channels
        self.server.internal_buffer = [[0.0, 0.0, 0.0, 0.0]] * (ymax + 1) * (xmax + 1)
        image_width = xmax - xmin + 1
        self.server.layer.rect = self.server.internal_buffer
        
        # just send back the same data
        self.request.sendall(struct.pack("I", 0))
        #print("buffer size %d" % pixel_size)
        self.got_setup = True
        get_data = True
        datas = 0

        unpack_time = 0
        copy_time = 0
        upload_time = 0
        last_update = -1
        while get_data:
            #get the first bit
            self.data = self.request.recv(2)
            cmd, other = struct.unpack("!bb", self.data)
            #print(cmd, other)

            if cmd == image_data:
                datas += 1
                #print('doing data')
                #the the window size
                self.data = self.request.recv(16)
                self.request.sendall(b"")
                w_xmin, w_xmax, w_ymin, w_ymax = struct.unpack("!IIII", self.data)
                #print("here comes pixels %d %d - %d - %d" %(w_xmin, w_ymin, w_xmax, w_ymax))
                num_pixels = int((w_xmax - w_xmin + 1)*(w_ymax - w_ymin + 1))
                buffer_size = int(num_pixels*pixel_size)

                #print("getting %d %d" % (buffer_size, num_pixels))
                #get the buffer
                self.data = self.request.recv(buffer_size)
                t = time.time()
                pixels = struct.unpack("f"*num_pixels*num_channels, self.data)
                
                #pixels = [(pixels[4*i+1], pixels[4*i+2], pixels[4*i+3], pixels[4*i]) for i in range(0, num_pixels)]  # make float array into rgba array
                unpack_time += time.time() - t

                window_width = w_xmax - w_xmin + 1
                
                t = time.time()
                scanline_start = (ymax - w_ymin)*image_width + xmin
                for y in range(w_ymin, w_ymax+1):
                    #self.server.layer.rect[scanline_start+w_xmin] = (1.0, 0.0, 0.0, 1.0)
                    #self.server.layer.rect[scanline_start] = (1.0, 0.0, 0.0, 1.0)
                    scanline_start = scanline_start - image_width
                    #print(self.server.layer.rect[0])
                    #print(scanline_start+w_xmin,scanline_start + w_xmax+1, window_width*y,window_width*(y + 1))
                    #print(self.server.layer.rect[scanline_start+w_xmin:scanline_start + w_xmax+1])
                    #print(pixels[window_width*(y-w_ymin):window_width*(y - w_ymin + 1)])
                    self.server.internal_buffer[scanline_start+w_xmin:scanline_start + w_xmax+1] = \
                        [(pixels[4*i+1], pixels[4*i+2], pixels[4*i+3], pixels[4*i]) for i in range(window_width*(y-w_ymin),window_width*(y - w_ymin + 1))]
                        #pixels[window_width*(y-w_ymin):window_width*(y - w_ymin + 1)]
                copy_time += time.time() - t


                t = time.time()
                if t - last_update > 1.0:
                    try:
                        self.server.layer.rect = self.server.internal_buffer
                        self.server.engine.update_result(self.server.result)
                    except:
                        print('error')
                        pass
                    upload_time += time.time() - t
                    last_update = t
                #print('done')

                #i = 0
                #for y in range(w_ymin, w_ymax+1):
                #    for x in range(w_xmin, w_xmax+1):
                #        self.server.layer.rect[(ymax - y)*(xmax+1) + x] = [pixels[4*i+1], pixels[4*i+2], pixels[4*i+3], pixels[4*i]]
                #        i += 1
                #pass
                #print(y*window_width + w_xmin,y*window_width + w_xmax + 1)
                #print(y*window_width,(y+1)*window_width)
                #print(len(pixels[y*window_width:(y+1)*window_width]))
                #print(self.server.layer.rect[y*window_width + w_xmin:y*window_width + w_xmax + 1])
                #print(pixels[y*window_width:(y+1)*window_width])
                #print(pixels[y*window_width:(y+1)*window_width])
                #pixel = self.server.layer.rect[0]
                #print(len(pixel))
                #print(type(pixel[0]), type(pixels[0][0]))    
                #self.server.layer.rect[y*window_width + w_xmin:y*window_width + w_xmax + 1] = \
                #    pixels[y*window_width:(y+1)*window_width]
                #TODO WRITE THIS OUT to buffer
                #print("received %d" % len(self.data))

            elif cmd == image_end:
                self.server.layer.rect = self.server.internal_buffer
                print("image done, %d datas" % datas)
                print("times ", unpack_time, copy_time, upload_time)
                #server.shutdown()
                return

