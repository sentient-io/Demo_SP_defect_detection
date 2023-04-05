import cv2 as cv
from multiprocessing.pool import ThreadPool
from collections import deque
from datetime import datetime, timedelta
import requests
import json
import base64

import asyncio

import argparse

parser = argparse.ArgumentParser(description='Face Recognize for video. Single face per frame.')
parser.add_argument('cam_id', help='camera Id')
parser.add_argument('out_url', help='Target API url to post results')

parser.add_argument('--mc_url', default="https://dev-apis.sentient.io/microservice/cv/sgpoly/v0/getpredictions", help='Defect detection microsrvice url')
parser.add_argument('--apikey', default="02C4C61EE7644727A76E", help='APIKEY')

conf_thres=0.1
iou_thres=0.1


interval = 3


class StatValue:
    def __init__(self, smooth_coef = 0.5):
        self.value = None
        self.smooth_coef = smooth_coef
    def update(self, v):
        if self.value is None:
            self.value = v
        else:
            c = self.smooth_coef
            self.value = c * self.value + (1.0-c) * v

def clock():
    return cv.getTickCount() / cv.getTickFrequency()



async def exec(cam_id, out_url, mc_url, apikey):

    def process_frame(fr, dt):
        print("process frame")
        headers = {
            'content-type': "application/json"
        }
        result, img_jpg_arr = cv.imencode('.jpg', fr, [cv.IMWRITE_JPEG_QUALITY, 100])
        img_jpg_bytes = img_jpg_arr.tobytes()        
        img_base64 = base64.b64encode(img_jpg_bytes).decode('utf-8')

        payload = {
            "image_base64": img_base64
        }
        print("before resp")

        resp = requests.request("POST",
                                    mc_url,
                                    data=json.dumps(payload),
                                    headers=headers)

        print(resp)
        results = resp.json()   
        print(resp.json())
        if(results['status'] == "Success"):
            annotated_fr = fr.copy()
            print("inside success")

            bgr_red=(255,0,0)
            bgr_green=(0,255,0)
            bgr_txt=(0,0,255)
            bgr_black = (0,0,0)
            bgr_white = (255,255,255)
            bgr=bgr_green
            height, width, _ = annotated_fr.shape

            if(results['results'] and results['results']['category'] and results['results']['category'] == 'scratch'):
                print("defect!!!")
                bgr=bgr_red
                cv.rectangle(annotated_fr,(0,0),(100,30), bgr_black, -1)
                cv.putText(annotated_fr, "Defect Confidence : {}".format(results['results']['confidence']), (10,10), cv.FONT_HERSHEY_SIMPLEX, 0.1, bgr_white, 2, cv.LINE_AA)

            print("plot rectangle!!!")

            cv.rectangle(annotated_fr,(0,0),(width,height), bgr, 3)
            
            _,img_jpg_arr_annotated = cv.imencode('.jpg', annotated_fr, [cv.IMWRITE_JPEG_QUALITY, 90])

            try:
                img_jpg_bytes_annotated = img_jpg_arr_annotated.tobytes() 
            except Exception as err:
                print(err)
            img_base64_annotated = base64.b64encode(img_jpg_bytes_annotated).decode('utf-8')
            result = {}
            result["Obj_det_output"] = {}
            result["timest"] = dt.strftime("%m/%d/%Y, %H:%M:%S") 
            result["image"] = img_base64_annotated    
            result["image_orig"] = img_base64   

            out_headers ={
                'content-type': "application/json"        
            }
            print("before websocket rest")
            response = requests.request("POST",
                                    out_url,
                                    data=json.dumps(result),
                                    headers=out_headers)

            print("respooo")


    threadn = cv.getNumberOfCPUs()
    pool = ThreadPool(processes = threadn)
    pending = deque()
    threaded_mode = True

    latency = StatValue()
    frame_interval = StatValue()
    last_frame_time = clock()
    interval =1
    start_time = datetime.now()


    cap = cv.VideoCapture(cam_id)

    frameId = 0    

    while  cap.isOpened():
        print("cap???")
        _ret, frame = cap.read()
        assert _ret
        fps = round(cap.get(cv.CAP_PROP_FPS)) 
        if(fps > 100):
            fps = 30

        multiplier = fps * interval

        print(frameId)
        if(frameId== 0):
            pool.apply_async(process_frame, args=(frame.copy(), datetime.now()))
            await asyncio.sleep(0.1)
        frameId = frameId+1
        if(frameId == multiplier):
            frameId = 0

        ch = cv.waitKey(1)
        if ch == 27:
            print("??")
            break

if __name__ == '__main__':

    kwargs = vars(parser.parse_args())
    asyncio.run(exec(cam_id=int(kwargs['cam_id']), out_url=kwargs['out_url'], mc_url=kwargs['mc_url'], apikey=kwargs['apikey']))




