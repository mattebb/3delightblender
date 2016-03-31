
import socketserver
import struct
import bpy
import time
import threading
import queue
import random
import copy

class Bucket:
    def __init__(self, x_size, y_size, x_start, y_start, pixel_size):
        self.x_min = x_start
        self.y_min = y_start
        self.x_max = x_start + x_size
        self.y_max = y_start + y_size
        self.data = bytearray(pixel_size*x_size*y_size)

    def set_data(self):
        pass

# a data structure of buckets of bytearrays
class BucketBuffer:
    def __init__(self,x_size, y_size, x_bucket_size, y_bucket_size, pixel_size):
        num_x_buckets = int(x_size/x_bucket_size)
        num_y_buckets = int(y_size/y_bucket_size)

        x_extra = x_size % x_bucket_size
        y_extra = y_size % y_bucket_size

        self.data = []
        for y in range(num_y_buckets):
            row = [Bucket(x_bucket_size, y_bucket_size, 
                          x*x_bucket_size, y*y_bucket_size,
                          pixel_size) for x in range(num_x_buckets)]
            if x_extra:
                row.append(Bucket(x_extra, y_bucket_size, 
                                  (num_x_buckets + 1)*x_bucket_size, 
                                  y*y_bucket_size, pixel_size))
            self.data.append(row)
        if y_extra:
            row = [Bucket(x_bucket_size, y_extra, 
                          x*x_bucket_size, 
                          (num_y_buckets + 1)*y_bucket_size,
                          pixel_size) for x in range(num_x_buckets)]
            if x_extra:
                row.append(Bucket(x_extra, y_extra, 
                                  (num_x_buckets + 1)*x_bucket_size, 
                                  (num_y_buckets + 1)*y_bucket_size, 
                                  pixel_size))
            self.data.append(row)

        self.x_bucket_size = x_bucket_size
        self.y_bucket_size = y_bucket_size
        self.x_extra = x_extra
        self.y_extra = y_extra

    def add_data(self, x_min, x_max, y_min, y_max, data):
        # if this is a full bucket just copy it!
        x = int(x_min / self.x_bucket_size)
        y = int(y_min / self.y_bucket_size)
        
        self.data[y][x].set_data(x_min, x_max, y_min, y_max, data)

    def flatten(self):
        pass

def copy_buffer(internal_buffer):
    buff = bytearray()
    for row in reversed(internal_buffer):
        buff.extend(row)

    return buff

def write_pixels_old(buffer_queue, xmax, ymax, num_channels, engine, result, layer):
    while True:
        pixels = buffer_queue.get()
        if not pixels:
            buffer_queue.get()
            buffer_queue.task_done()
            return
        #self.write_time -= time.time()
        #self.unpack_time -= time.time()
        pixels = struct.unpack("f"*(ymax + 1)*(xmax + 1) * num_channels, copy_buffer(pixels))
        layer.rect = [(pixels[4*i+1], 
            pixels[4*i+2], 
            pixels[4*i+3], 
            pixels[4*i]) for i in range(len(layer.rect))]

        engine.update_result(result)
        buffer_queue.task_done()
        #print("done writing")
        #self.write_time += time.time()

def process_bucket_old(bucket_queue, buffer_queue, xmax, ymax, pixel_size):
    t = time.time()
    internal_buffer = [bytearray((xmax + 1) * pixel_size) for i in range(ymax +1)]
    while True:
        #print(self.bucket_queue.qsize())
        pixels = bucket_queue.get()
        if not pixels:
            buffer_queue.join()
            buffer_queue.put(internal_buffer)
            buffer_queue.join()
            bucket_queue.task_done()
            return
        w_xmin, w_xmax, w_ymin, w_ymax, pixel_data = pixels
        window_width = (w_xmax - w_xmin + 1)* pixel_size
        x_start = w_xmin*pixel_size
        x_end = (w_xmax+1)*pixel_size
        for y in range(w_ymin, w_ymax+1):
            internal_buffer[y][x_start:x_end] = pixel_data[(y-w_ymin)*window_width:(y-w_ymin+1)*window_width]

            #f = time.time()
            #processing_time += f
            #sub_processing_time += f
        if time.time() - t > 5 and bucket_queue.empty():
            try:
                buffer_queue.put_nowait(copy.copy(internal_buffer))
            except:
                pass
            t = time.time()
          
        bucket_queue.task_done()

def flip_x(pixel_list, width, height):
    out_list = []
    for y in range(height):
        out_list.extend(pixel_list[y*width:(y+1)*width])
    return out_list

def process_bucket(bucket_queue, engine, num_channels):
    t = time.time()
    while True:
        #print(self.bucket_queue.qsize())
        pixels = bucket_queue.get()
        if not pixels:
            #bucket_queue.get()
            bucket_queue.task_done()
            return
        w_xmin, w_xmax, w_ymin, w_ymax, pixel_data = pixels
        width = w_xmax - w_xmin + 1
        height = w_ymax - w_ymin + 1
        pixel_data = struct.unpack("f"*(height)*(width) * num_channels, pixel_data) #copy_buffer(pixel_data))
        result = engine.begin_result(w_xmin, w_ymin, width, height)
        pixel_data = [(pixel_data[4*i+1], 
            pixel_data[4*i+2], 
            pixel_data[4*i+3], 
            pixel_data[4*i]) for i in range(len(result.layers[0].passes[0].rect))]
        #pixel_data = flip_x(pixel_data, width, height)

        #print(type(pixel_data), len(pixel_data), type(result.layers[0].passes[0].rect), len(result.layers[0].passes[0].rect))
        result.layers[0].passes[0].rect = pixel_data
        engine.end_result(result)

        bucket_queue.task_done()
          
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
        #print('doing setup')
        self.server.is_done = False
        self.data = self.request.recv(1024)
        data = self.data.split(b";")
        #0 is image name
        image_name = data[0].decode('utf-8')[1:]
        #print(image_name)
        #then dspy params
        dspy_params = data[1]
        #print(dspy_params)
        
        self.data = data[2]
        #we need 36 bytes here
        if len(self.data) < 33: 
            self.data += self.request.recv(36)
        xmin, xmax, ymin, ymax, a_len, z_len, channel_len, num_channels, merge = struct.unpack("!IIIIIIIIb", self.data[1:])
        print(xmin, xmax, ymin, ymax)
        #print(a_len, z_len, channel_len, num_channels)
        pixel_size = int(a_len/8) + int(z_len/8) + int(channel_len/8 * num_channels) #bits ->bytes
        num_channels = num_channels + 1 if a_len > 0 else num_channels
        num_channels = num_channels + 1 if z_len > 0 else num_channels
        pixel_size = num_channels * 4
        image_stride = (xmax - xmin + 1)*pixel_size
        #internal_buffer = [bytearray((xmax + 1) * pixel_size) for i in range(ymax +1)]
        #internal_buffer = BucketBuffer(xmax + 1, ymax + 1, 16, 16, pixel_size)
        #print(len(internal_buffer), len(internal_buffer[0]))

        self.ymax = ymax
        self.xmax = xmax
        self.num_channels = num_channels
        self.pixel_size = pixel_size
        
        print("setting up")
        #print(len(internal_buffer)/4)
        #self.server.layer.rect = self.server.internal_buffer
        
        # just send back the same data
        self.request.sendall(struct.pack("I", 0))
        #print("buffer size %d" % pixel_size)
        self.got_setup = True
        get_data = True
        datas = 0

        unpack_time = 0
        copy_time = 0
        upload_time = 0
        bucket_queue = queue.Queue(-1)
        #buffer_queue = queue.Queue(1)

        #writing_worker = threading.Thread(target=write_pixels, 
        #    args=(buffer_queue, xmax, ymax, num_channels, 
        #        self.server.engine, self.server.result, self.server.layer))
        #writing_worker.setDaemon(True)
        #writing_worker.start()

        bucket_worker = threading.Thread(target=process_bucket, 
            args=(bucket_queue, self.server.engine, num_channels))
        bucket_worker.setDaemon(True)
        bucket_worker.start()
        
        t = time.time()
        sub_processing_time = 0
        processing_time = 0
        copy_time = 0
        receiving_time = 0
        self.write_time = 0
        self.unpack_time = 0
        total_time = 0
        while get_data:
            #get the first bit
            data = self.request.recv(2)
            cmd, other = struct.unpack("!bb", data)
            #start_time = time.time()
            #print(cmd, other)

            if cmd == image_data:
                #total_time -= time.time()
                #processing_time -= time.time()
                #datas += 1
                #print('doing data')
                #the the window size
                receiving_data = self.request.recv(16)
                #self.request.sendall(b"")
                w_xmin, w_xmax, w_ymin, w_ymax = struct.unpack("!IIII", receiving_data)
                #print("here comes pixels %d %d - %d - %d" %(w_xmin, w_ymin, w_xmax, w_ymax))
                #print("bucket size = %d x %d" %(w_xmax- w_xmin+1, w_ymax - w_ymin+1))
                #num_pixels = (w_xmax - w_xmin + 1)*(w_ymax - w_ymin + 1)
                #buffer_size = num_pixels*pixel_size

                #print("getting data" )
                #get the buffer
                receiving_time -= time.time()
                bucket_queue.put_nowait((w_xmin, w_xmax, w_ymin, w_ymax, self.request.recv((w_xmax - w_xmin + 1)*(w_ymax - w_ymin + 1)*pixel_size)))
                #pixel_data = self.request.recv((w_xmax - w_xmin + 1)*(w_ymax - w_ymin + 1)*pixel_size)
                receiving_time += time.time()
                #t = time.time()
                #sub_processing_time -= time.time()
                
                #internal_buffer.add_data(w_xmin, w_xmax, w_ymin, w_ymax, pixel_data)

                #window_width = (w_xmax - w_xmin + 1)*pixel_size
                #x_start = w_xmin*pixel_size
                #x_end = (w_xmax+1)*pixel_size
                #for y in range(w_ymin, w_ymax+1):
                #    internal_buffer[y][x_start:x_end] = pixel_data[(y-w_ymin)*window_width:(y-w_ymin+1)*window_width]

                #f = time.time()
                #processing_time += f
                #sub_processing_time += f
                #if time.time() - t > 1 and self.buffer_queue.empty():
                #    t = time.time()
                #    copy_time -= t
                #    self.buffer_queue.put_nowait(self.copy_buffer(internal_buffer))
                #    #self.buffer_queue.put_nowait(internal_buffer.flatten())
                #    copy_time += time.time()
                #total_time += time.time()
                

            elif cmd == image_end:
                print('image end')
                bucket_queue.put(0)
                bucket_queue.join()
                #print("waiting to finish")
                #buffer_queue.join()
                print("finished")
                #self.server.engine.end_result(self.server.result)
            
                self.server.is_done = True
                #print("image done, %d datas" % datas)
                print("times ", receiving_time, sub_processing_time, processing_time, copy_time,
                      self.write_time, self.unpack_time, total_time)
                #server.shutdown()
                return

