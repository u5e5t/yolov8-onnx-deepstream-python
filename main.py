#!/usr/bin/env python3

import sys
sys.path.append('../')
import gi
gi.require_version('Gst', '1.0')

from gi.repository import Gst,GLib
from common.bus_call import bus_call

import pyds
import configparser
from common.FPS import PERF_DATA

import math

PGIE_CFIG_PATH = r'./cfig/config_pgie_yolov8.txt'

TRACKER_CFIG_PATH = r'./cfig/config_tracker.txt'

filepath = 'test23123.mp4'



gpu_id = 0
width = 1280
height = 720
perf_data = None
# 视频路径可以是rtsp流，也可以是本地视频
rtsps = ['file:///root/VID_20230511_153812.mp4']


def osd_sink_pad_buffer_probe(pad,info,u_data):
    """探针函数，设置osd绘制框与帧率检测"""
    gst_buffer = info.get_buffer()
    
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))    
    l_frame = batch_meta.frame_meta_list
    while l_frame is not None:
        try:
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break
        stream_index = "stream{0}".format(frame_meta.pad_index)
        
        # 帧率更新计算
        global perf_data
        perf_data.update_fps(stream_index)
  
        l_obj=frame_meta.obj_meta_list
        while l_obj is not None:
            try:
                # Casting l_obj.data to pyds.NvDsObjectMeta
                obj_meta=pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                break

            obj_meta.text_params.set_bg_clr = 1
            obj_meta.text_params.text_bg_clr.red = 0.0
            obj_meta.text_params.text_bg_clr.green = 0.0
            obj_meta.text_params.text_bg_clr.blue = 0.0
            obj_meta.text_params.text_bg_clr.alpha = 0.0

            obj_meta.text_params.font_params.font_color.red = 1.0
            obj_meta.text_params.font_params.font_color.green = 1.0
            obj_meta.text_params.font_params.font_color.blue = 0.0
            obj_meta.text_params.font_params.font_color.alpha = 1.0
            obj_meta.text_params.font_params.font_size = 12

            try: 
                l_obj=l_obj.next
                # l_user = l_user.next
            except StopIteration:
                break
            
        try:
            l_frame=l_frame.next
        except StopIteration:
            break
    return Gst.PadProbeReturn.OK

def cb_newpad(decodebin, decoder_src_pad,data):
    print("In cb_newpad\n")
    caps=decoder_src_pad.get_current_caps()
    gststruct=caps.get_structure(0)
    gstname=gststruct.get_name()
    source_bin=data
    features=caps.get_features(0)

    # Need to check if the pad created by the decodebin is for video and not
    # audio.
    print("gstname=",gstname)
    if(gstname.find("video")!=-1):
        # Link the decodebin pad only if decodebin has picked nvidia
        # decoder plugin nvdec_*. We do this by checking if the pad caps contain
        # NVMM memory features.
        print("features=",features)
        if features.contains("memory:NVMM"):
            # Get the source bin ghost pad
            bin_ghost_pad=source_bin.get_static_pad("src")
            if not bin_ghost_pad.set_target(decoder_src_pad):
                sys.stderr.write("Failed to link decoder src pad to source bin ghost pad\n")
        else:
            sys.stderr.write(" Error: Decodebin did not pick nvidia decoder plugin.\n")

def decodebin_child_added(child_proxy,Object,name,user_data):
    print("Decodebin child added:", name, "\n")
    if(name.find("decodebin") != -1):
        Object.connect("child-added",decodebin_child_added,user_data)

def create_source_bin(index,uri):
    print("Creating source bin")

    # Create a source GstBin to abstract this bin's content from the rest of the
    # pipeline
    bin_name="source-bin-%02d" %index
    print(bin_name)
    nbin=Gst.Bin.new(bin_name)
    if not nbin:
        sys.stderr.write(" Unable to create source bin \n")

    # Source element for reading from the uri.
    # We will use decodebin and let it figure out the container format of the
    # stream and the codec and plug the appropriate demux and decode plugins.
    uri_decode_bin=Gst.ElementFactory.make("uridecodebin", "uri-decode-bin")
    if not uri_decode_bin:
        sys.stderr.write(" Unable to create uri decode bin \n")
    # We set the input uri to the source element
    uri_decode_bin.set_property("uri",uri)
    # Connect to the "pad-added" signal of the decodebin which generates a
    # callback once a new pad for raw data has beed created by the decodebin
    uri_decode_bin.connect("pad-added",cb_newpad,nbin)
    uri_decode_bin.connect("child-added",decodebin_child_added,nbin)

    # We need to create a ghost pad for the source bin which will act as a proxy
    # for the video decoder src pad. The ghost pad will not have a target right
    # now. Once the decode bin creates the video decoder and generates the
    # cb_newpad callback, we will set the ghost pad target to the video decoder
    # src pad.
    Gst.Bin.add(nbin,uri_decode_bin)
    bin_pad=nbin.add_pad(Gst.GhostPad.new_no_target("src",Gst.PadDirection.SRC))
    if not bin_pad:
        sys.stderr.write(" Failed to add ghost pad in source bin \n")
        return None
    return nbin

def detect():
    
    #初始化
    Gst.init(None)
    pipeline = Gst.Pipeline() 
    
    # 元件声明及属性设置
    streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")
    pipeline.add(streammux)
    number_sources = rtsps
    
    global perf_data
    perf_data = PERF_DATA(len(number_sources))
    ## url
    for i in range(len(number_sources)):
        print("Creating source_bin ",i," \n ")
        uri_name=number_sources[i]

        source_bin=create_source_bin(i, uri_name)
        if not source_bin:
            sys.stderr.write("Unable to create source bin \n")
        pipeline.add(source_bin)
        padname="sink_%u" %i
        sinkpad= streammux.get_request_pad(padname) 
        if not sinkpad:
            sys.stderr.write("Unable to create sink pad bin \n")
        srcpad=source_bin.get_static_pad("src")
        if not srcpad:
            sys.stderr.write("Unable to create src pad bin \n")
        srcpad.link(sinkpad)
       
    primary_detector = Gst.ElementFactory.make("nvinfer", "primary-inference")
    
    nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "nvvid-converter")
    nvvidconv1 = Gst.ElementFactory.make("nvvideoconvert", "nvvid-converter1")
    
    nvosd = Gst.ElementFactory.make("nvdsosd", "nv-onscreendisplay")

    caps = Gst.ElementFactory.make("capsfilter", "filter")
    tiler=Gst.ElementFactory.make("nvmultistreamtiler", "nvtiler")
    
    tracker = Gst.ElementFactory.make("nvtracker","tracker")
    
    queue1=Gst.ElementFactory.make("queue","queue1")
    queue2=Gst.ElementFactory.make("queue","queue2")
    queue5=Gst.ElementFactory.make("queue","queue5")
    queue6=Gst.ElementFactory.make("queue","queue6")
    queue7=Gst.ElementFactory.make("queue","queue7")
    queue8=Gst.ElementFactory.make("queue","queue8")
    queue9=Gst.ElementFactory.make("queue","queue9")
    
    sink = Gst.ElementFactory.make("filesink", "sink")

    streammux.set_property('width', width)
    streammux.set_property('height', height)
    streammux.set_property('batch-size', len(number_sources))
    streammux.set_property('batched-push-timeout', 4000)
    streammux.set_property('enable-padding', 1)
    streammux.set_property('gpu_id',gpu_id)
    
    tiler_rows=int(math.sqrt(len(number_sources)))
    tiler_columns=int(math.ceil((1.0*len(number_sources))/tiler_rows))
    tiler.set_property("rows",tiler_rows)
    tiler.set_property("columns",tiler_columns)
    tiler.set_property("width", width)
    tiler.set_property("height", height)
    tiler.set_property("gpu_id", gpu_id)
    
    primary_detector.set_property('config-file-path', PGIE_CFIG_PATH)
    pgie_batch_size=primary_detector.get_property("batch-size")
    if(pgie_batch_size != len(number_sources)):
        primary_detector.set_property("batch-size",len(number_sources))
        
    config = configparser.ConfigParser()
    config.read(TRACKER_CFIG_PATH)
    config.sections()
    for key in config['tracker']:
        if key == 'tracker-width' :
            tracker_width = config.getint('tracker', key)
            tracker.set_property('tracker-width', tracker_width)
        if key == 'tracker-height' :
            tracker_height = config.getint('tracker', key)
            tracker.set_property('tracker-height', tracker_height)
        if key == 'gpu-id' :
            tracker_gpu_id = config.getint('tracker', key)
            tracker.set_property('gpu_id', tracker_gpu_id)
        if key == 'll-lib-file' :
            tracker_ll_lib_file = config.get('tracker', key)
            tracker.set_property('ll-lib-file', tracker_ll_lib_file)
        if key == 'll-config-file' :
            tracker_ll_config_file = config.get('tracker', key)
            tracker.set_property('ll-config-file', tracker_ll_config_file)
        if key == 'display-tracking-id' :
            tracker_display_tracking_id= config.getint('tracker', key)
            tracker.set_property('display-tracking-id', tracker_display_tracking_id) 
        if key == 'enable-batch-process' :
            tracker_enable_batch_process = config.getint('tracker', key)
            tracker.set_property('enable_batch_process', tracker_enable_batch_process)        

    caps.set_property(
        "caps", Gst.Caps.from_string("memory:NVMM, video/x-raw, format, G_TYPE_STRING, I420")
    )
    
    sink.set_property("location", filepath)
    sink.set_property("sync", 0)
    sink.set_property("async", 0)
    
    encoder = Gst.ElementFactory.make("avenc_mpeg4", "encoder")
    if not encoder:
        sys.stderr.write(" Unable to create encoder \n")
    encoder.set_property("bitrate", 2000000)
    print("Creating Code Parser \n")
    codeparser = Gst.ElementFactory.make("mpeg4videoparse", "mpeg4-parser")
    if not codeparser:
        sys.stderr.write(" Unable to create code parser \n")
    print("Creating Container \n")
    container = Gst.ElementFactory.make("qtmux", "qtmux")
    
    loop = GLib.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect ("message", bus_call, loop)

    # 添加到pipeline中
    pipeline.add(primary_detector)
    pipeline.add(tracker)
    pipeline.add(queue1)
    pipeline.add(queue2)
    pipeline.add(queue5)
    pipeline.add(queue6)
    pipeline.add(queue7)
    pipeline.add(queue8)
    pipeline.add(queue9)
    pipeline.add(nvvidconv)
    pipeline.add(nvosd)
    pipeline.add(tiler)
    pipeline.add(sink)
    pipeline.add(nvvidconv1)
    pipeline.add(encoder)
    pipeline.add(caps)
    pipeline.add(codeparser)
    pipeline.add(container)
    
    # 元件连接
    streammux.link(queue1)
    queue1.link(primary_detector)
    primary_detector.link(queue2)
    queue2.link(tracker)
    tracker.link(queue5)
    queue5.link(tiler)
    tiler.link(queue6)
    queue6.link(nvvidconv)
    nvvidconv.link(queue7)
    queue7.link(nvosd)
    nvosd.link(queue8)  
    # queue8.link(sink)
    queue8.link(nvvidconv1)    
    nvvidconv1.link(caps)    
    caps.link(queue9)    
    queue9.link(encoder)    
    encoder.link(codeparser)
    codeparser.link(container)
    container.link(sink)
    
    # 探针插入
    osd_sink_pad = nvosd.get_static_pad("sink")
    osd_sink_pad.add_probe(Gst.PadProbeType.BUFFER, osd_sink_pad_buffer_probe, 
                               0)
    
    # 定时器定时打印帧率 
    GLib.timeout_add(5000, perf_data.perf_print_callback)
    
    print("Now playing: " )
    pipeline.set_state(Gst.State.PLAYING)
    
    print("Running...")
    try:
        loop.run()
    except:
        pass

    #Out of the main loop, clean up nicely
    print("Returned, stopping playback")
    pipeline.set_state(Gst.State.NULL)
    

if __name__ == '__main__':
    
    detect()
