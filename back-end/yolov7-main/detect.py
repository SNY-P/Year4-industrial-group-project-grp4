import argparse
import time
import os
from pathlib import Path
from datetime import datetime

import csv
import cv2
import torch
import torch.backends.cudnn as cudnn
from numpy import random

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from models.experimental import attempt_load
from utils.datasets import LoadStreams, LoadImages
from utils.general import check_img_size, check_requirements, check_imshow, non_max_suppression, apply_classifier, \
    scale_coords, xyxy2xywh, strip_optimizer, set_logging, increment_path
from utils.plots import plot_one_box
from utils.torch_utils import select_device, load_classifier, time_synchronized, TracedModel

import dbConnect

## Requires a dataset to run

def detect(save_img=False):
    source, weights, view_img, save_txt, imgsz, trace = opt.source, opt.weights, opt.view_img, opt.save_txt, opt.img_size, not opt.no_trace
    save_img = not opt.nosave and not source.endswith('.txt')  # save inference images
    webcam = source.isnumeric() or source.endswith('.txt') or source.lower().startswith(
        ('rtsp://', 'rtmp://', 'http://', 'https://'))

    # Directories
    save_dir = Path(increment_path(Path(opt.project) / opt.name, exist_ok=opt.exist_ok))  # increment run
    (save_dir / 'labels' if save_txt else save_dir).mkdir(parents=True, exist_ok=True)  # make dir

    # Initialize
    set_logging()
    device = select_device(opt.device)
    half = device.type != 'cpu'  # half precision only supported on CUDA

    # Load model
    model = attempt_load(weights, map_location=device)  # load FP32 model
    stride = int(model.stride.max())  # model stride
    imgsz = check_img_size(imgsz, s=stride)  # check img_size

    if trace:
        model = TracedModel(model, device, opt.img_size)

    if half:
        model.half()  # to FP16

    # Second-stage classifier
    classify = False
    if classify:
        modelc = load_classifier(name='resnet101', n=2)  # initialize
        modelc.load_state_dict(torch.load('weights/resnet101.pt', map_location=device)['model']).to(device).eval()

    # Set Dataloader
    vid_path, vid_writer = None, None
    if webcam:
        view_img = check_imshow()
        cudnn.benchmark = True  # set True to speed up constant image size inference
        dataset = LoadStreams(source, img_size=imgsz, stride=stride)
    else:
        dataset = LoadImages(source, img_size=imgsz, stride=stride)

    # Get names and colors
    names = model.module.names if hasattr(model, 'module') else model.names
    colors = [[random.randint(0, 255) for _ in range(3)] for _ in names]

    # Run inference
    if device.type != 'cpu':
        model(torch.zeros(1, 3, imgsz, imgsz).to(device).type_as(next(model.parameters())))  # run once
    old_img_w = old_img_h = imgsz
    old_img_b = 1

    t0 = time.time()

    ## Get file name from parser
    print("file name",opt.source)
    fileName = opt.source
    ti_m = os.path.getctime(fileName)
    t_obj = time.localtime(ti_m)
    counter = 0

    for path, img, im0s, vid_cap in dataset:
        # Initialise Results List
        resultList = []

        img = torch.from_numpy(img).to(device)
        img = img.half() if half else img.float()  # uint8 to fp16/32
        img /= 255.0  # 0 - 255 to 0.0 - 1.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)

        # Warmup
        if device.type != 'cpu' and (old_img_b != img.shape[0] or old_img_h != img.shape[2] or old_img_w != img.shape[3]):
            old_img_b = img.shape[0]
            old_img_h = img.shape[2]
            old_img_w = img.shape[3]
            for i in range(3):
                model(img, augment=opt.augment)[0]

        # Inference
        t1 = time_synchronized()
        with torch.no_grad():   # Calculating gradients would cause a GPU memory leak
            pred = model(img, augment=opt.augment)[0]
        t2 = time_synchronized()

        # Apply NMS
        pred = non_max_suppression(pred, opt.conf_thres, opt.iou_thres, classes=opt.classes, agnostic=opt.agnostic_nms)
        t3 = time_synchronized()

        # Apply Classifier
        if classify:
            pred = apply_classifier(pred, modelc, img, im0s)

        # Process detections
        for i, det in enumerate(pred):  # detections per image
            if webcam:  # batch_size >= 1
                p, s, im0, frame = path[i], '%g: ' % i, im0s[i].copy(), dataset.count
            else:
                p, s, im0, frame = path, '', im0s, getattr(dataset, 'frame', 0)

            p = Path(p)  # to Path
            save_path = str(save_dir / p.name)  # img.jpg
            txt_path = str(save_dir / 'labels' / p.stem) + ('' if dataset.mode == 'image' else f'_{frame}')  # img.txt
            gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
            if len(det):
                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()

                ##############################################################################
                # KYLE CODE
                # ############################################################################  
                 
                # Print results and store in list with timestamp
                for c in det[:, -1].unique():
                    n = (det[:, -1] == c).sum()  # detections per class
                    s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string
                

                # Timestamp
                currentTime = datetime.now()
                timeToStr = currentTime.strftime("%H:%M:%S")
                s += timeToStr
                resultList.append(s)

                # Append data to database
                for i in resultList:
                    print(i)
                    cars = 0
                    truck = 0
                    buses = 0
                    motorcycles = 0
                    bicycles = 0
                    timeMark = ""
                    tokens = [x.strip() for x in i.split(',')]
                    for j in tokens:
                        if "car" in j:
                            cars += int(j[:2])
                        elif "truck" in j:
                            truck += int(j[:2])
                        elif "bus" in j:
                            buses += int(j[:2])
                        elif "motorcycle" in j:
                            motorcycles += int(j[:2])
                        elif "bicycle" in j:
                            bicycles += int(j[:2])
                        elif ":" in j:
                            timeMark += j
                    # numResultList.append([cars,truck,buses,motorcycles,bicycles, timeMark])
                    # add data to table
                    values = (cars, truck, buses, motorcycles, bicycles, timeMark)
                    dbConnect.insert_data_into_table("vehicledetection", values)

                # startTime = currentTime
                # timeDiff = (currentTime - startTime).total_seconds()
                # if timeDiff > 1:
                    
                #     s += timeToStr
                #     resultList.append(s)
                
                # if counter%24 == 0:
                #     t_obj = time.localtime(time.mktime(t_obj)+1)
                # fin = time.strftime("%H:%M:%S", t_obj)
                # s += fin
                # resultList.append(s)
                # counter +=1
                # print(resultList)

                # Write results
                for *xyxy, conf, cls in reversed(det):
                    if save_txt:  # Write to file
                        xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
                        line = (cls, *xywh, conf) if opt.save_conf else (cls, *xywh)  # label format
                        with open(txt_path + '.txt', 'a') as f:
                            f.write(('%g ' * len(line)).rstrip() % line + '\n')

                    if save_img or view_img:  # Add bbox to image
                        label = f'{names[int(cls)]} {conf:.2f}'
                        plot_one_box(xyxy, im0, label=label, color=colors[int(cls)], line_thickness=1)

            # Print time (inference + NMS)
            print(f'{s}Done. ({(1E3 * (t2 - t1)):.1f}ms) Inference, ({(1E3 * (t3 - t2)):.1f}ms) NMS')

            # Stream results
            if view_img:
                cv2.imshow(str(p), im0)
                cv2.waitKey(1)  # 1 millisecond

            # Save results (image with detections)
            if save_img:
                if dataset.mode == 'image':
                    cv2.imwrite(save_path, im0)
                    print(f" The image with the result is saved in: {save_path}")
                else:  # 'video' or 'stream'
                    if vid_path != save_path:  # new video
                        vid_path = save_path
                        if isinstance(vid_writer, cv2.VideoWriter):
                            vid_writer.release()  # release previous video writer
                        if vid_cap:  # video
                            fps = vid_cap.get(cv2.CAP_PROP_FPS)
                            w = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            h = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        else:  # stream
                            fps, w, h = 30, im0.shape[1], im0.shape[0]
                            save_path += '.mp4'
                        vid_writer = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
                    vid_writer.write(im0)

    if save_txt or save_img:
        s = f"\n{len(list(save_dir.glob('labels/*.txt')))} labels saved to {save_dir / 'labels'}" if save_txt else ''
        print(f"Results saved to {save_dir}{s}")

    print(f'Done. ({time.time() - t0:.3f}s)')

    # Initialise final list to write to file
    numResultList = []

    # Convert detections into int using string handling
    # (KYLE) Could clean this up? looks messy
    # for i in resultList:
    #     print(i)
    #     cars = 0
    #     truck = 0
    #     buses = 0
    #     motorcycles = 0
    #     bicycles = 0
    #     timeMark = ""
    #     tokens = [x.strip() for x in i.split(',')]
    #     for j in tokens:
    #         if "car" in j:
    #             cars += int(j[:2])
    #         elif "truck" in j:
    #             truck += int(j[:2])
    #         elif "bus" in j:
    #             buses += int(j[:2])
    #         elif "motorcycle" in j:
    #             motorcycles += int(j[:2])
    #         elif "bicycle" in j:
    #             bicycles += int(j[:2])
    #         elif ":" in j:
    #             timeMark += j
    #     # numResultList.append([cars,truck,buses,motorcycles,bicycles, timeMark])
    #     # add data to table
    #     values = (cars, truck, buses, motorcycles, bicycles, timeMark)
    #     dbConnect.insert_data_into_table("vehicledetection", values)
    #     # dbConnect.create_line_graph()

    # Create graph and store it in runs folder
    results_path = str(save_dir / p.stem) + ('' if dataset.mode == 'image' else f'_data')  # img.txt
    dbConnect.create_line_graph(results_path)

    # If file doesn't exist, create a new one. If existing data is present, overwrite data
    # (KYLE) May need to look at this again incase we want more data stored
    # Every 50 frames, results are written to runs\detect\exp*\videoname_no_of_frames.txt   
    # results_path = str(save_dir / p.stem) + ('' if dataset.mode == 'image' else f'_data')  # img.txt
    
    # with open(results_path +'.txt', 'x') as fp:
    #     fp.write("Cars, Truck, Buses, Motorcycles, Bicycles, Time, \n")
    #     o = 0
    #     for i in numResultList:
    #         if(o % 50==0):
    #             fp.write("%s" % i)
    #             fp.write(",\n")
    #         o +=1
    #     print("Finished writing to file")

    # fp.close()
    # # Remove brackets from file and convert to CSV
    # with open(results_path +'.txt', 'r') as fp:
    #     data = fp.read()
        
    # data = data.replace('[', '')
    # data = data.replace(']', '')

    # with open(results_path +'.txt', 'w') as fp:
    #     fp.write(data)
    # fp.close()
    
    # df = pd.read_csv(results_path +'.txt', sep=",")
    # df.to_csv(results_path +'.csv', index=None)
    
    #Create graph and save it as png (obviously would need to modify make it nicer)
    # graph = pd.read_csv(results_path +'.csv')
    # print(graph.head())
    # graph.plot()
    # plt.savefig(results_path +'.png')

#############################################################################
############################################################################# 

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str, default='yolov7.pt', help='model.pt path(s)')
    parser.add_argument('--source', type=str, default='inference/images', help='source')  # file/folder, 0 for webcam
    parser.add_argument('--img-size', type=int, default=640, help='inference size (pixels)')
    parser.add_argument('--conf-thres', type=float, default=0.25, help='object confidence threshold')
    parser.add_argument('--iou-thres', type=float, default=0.45, help='IOU threshold for NMS')
    parser.add_argument('--device', default='', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    parser.add_argument('--view-img', action='store_true', help='display results')
    parser.add_argument('--save-txt', action='store_true', help='save results to *.txt')
    parser.add_argument('--save-conf', action='store_true', help='save confidences in --save-txt labels')
    parser.add_argument('--nosave', action='store_true', help='do not save images/videos')
    parser.add_argument('--classes', nargs='+', type=int, help='filter by class: --class 0, or --class 0 2 3')
    parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
    parser.add_argument('--augment', action='store_true', help='augmented inference')
    parser.add_argument('--update', action='store_true', help='update all models')
    parser.add_argument('--project', default='runs/detect', help='save results to project/name')
    parser.add_argument('--name', default='', help='save results to project/name')
    parser.add_argument('--exist-ok', action='store_true', help='existing project/name ok, do not increment')
    parser.add_argument('--no-trace', action='store_true', help='don`t trace model')
    opt = parser.parse_args()
    print(opt)
    svc_name = "source"
    #check_requirements(exclude=('pycocotools', 'thop'))

    with torch.no_grad():
        if opt.update:  # update all models (to fix SourceChangeWarning)
            for opt.weights in ['yolov7.pt']:
                detect()
                strip_optimizer(opt.weights)
        else:
            detect()
