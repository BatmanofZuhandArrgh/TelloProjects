import cv2
import pygame
import time
import numpy as np

from move import Controls

import mediapipe as mp
mp_face_detection = mp.solutions.face_detection
mp_drawing = mp.solutions.drawing_utils

class FaceTracker(Controls):
    """ 
    Once the drone detect a face it will follow that face, face to face    
    """

    def __init__(self):
        super(FaceTracker, self).__init__()
        self.area_to_stabilize = (25000, 30000)
        self.height = 720
        self.width = 960

        self.upper_limit = int(self.height//3)
        self.lower_limit = self.upper_limit * 2
        
        self.rightmost_limit = int(self.width//3)
        self.leftmost_limit = self.rightmost_limit*2
        
    def run(self):
        self.start_up()

        frame_read = self.tello.get_frame_read()

        should_stop = False
        while not should_stop:

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    should_stop = True
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        should_stop = True
                    elif event.key == pygame.K_t:
                        self.tello.takeoff()
                        self.send_rc_control = True

                    elif key == pygame.K_l:  # land
                        self.tello.land()
                        self.send_rc_control = False
            
            if frame_read.stopped:
                break

            self.screen.fill([0, 0, 0])
            self.update()

            frame = frame_read.frame                

            text = "Battery: {}%".format(self.tello.get_battery())
            cv2.putText(frame, text, (5, 720 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            frame, [self.face_coords, self.area] = findFace(frame)
            
            #Move in left right up down
            if(self.face_coords == [0,0]):
                print('stationary`')
                self.stationary()
                continue
            else:
                if(self.face_coords[1] < self.upper_limit):
                    print('down')
                    self.up_down_velocity = -self.S
                elif(self.face_coords[1] > self.lower_limit):
                    print('up')
                    self.up_down_velocity = self.S
                else:
                    self.up_down_velocity = 0
                    print('center')

                if(self.face_coords[0] < self.rightmost_limit):
                    self.left_right_velocity = -self.S
                    print('move_left')
                elif(self.face_coords[0] > self.leftmost_limit):
                    self.left_right_velocity = self.S
                    print('move_right')
                else:
                    self.left_right_velocity = 0
                    print('center')
            
            #Move forward, backward
            if(self.area == 0):
                self.stationary()
                continue
            else:
                if(self.area > self.area_to_stabilize[-1]):
                    self.for_back_velocity = -self.S
                    print('move backwards')
                elif(self.area < self.area_to_stabilize[0]):
                    self.for_back_velocity = self.S
                    print('move forwards')
                else:
                    self.for_back_velocity = 0
                    print('stationary')

            self.update()
            
            #Draw grid
            cv2.line(frame, (0,self.lower_limit),(self.width, self.lower_limit), (255, 0, 0), 1, 1)
            cv2.line(frame, (0,self.upper_limit),(self.width, self.upper_limit), (255, 0, 0), 1, 1)
            
            cv2.line(frame, (self.rightmost_limit, 0),(self.rightmost_limit, self.height), (255, 0, 0), 1, 1)
            cv2.line(frame, (self.leftmost_limit, 0),(self.leftmost_limit, self.height), (255, 0, 0), 1, 1)

            cv2.putText(img = frame, text = f'{self.face_coords}_{self.area}', 
                        org = (30,30), fontFace = cv2.FONT_HERSHEY_SIMPLEX, 
                        fontScale = 1,color = (0, 0, 255), thickness = 2)


            frame = np.rot90(frame)
            frame = np.flipud(frame)

            frame = pygame.surfarray.make_surface(frame)
            self.screen.blit(frame, (0, 0))
            pygame.display.update()

            time.sleep(1 / self.FPS)

        self.tello.streamoff()
        # Call it always before finishing. To deallocate resources.
        self.tello.end()

    def update(self):
        """ Update routine. Send velocities to Tello."""
        if self.send_rc_control:
            self.tello.send_rc_control(self.left_right_velocity, self.for_back_velocity,
                self.up_down_velocity, self.yaw_velocity)

def findFace(img, mode = 'CascadeClassifier'):
    if mode == 'CascadeClassifier':
        faceCascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = faceCascade.detectMultiScale(imgGray, 1.2, 8)
    elif mode == 'BlazeFace':
        with mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) as face_detection:
            # Convert the BGR image to RGB and process it with MediaPipe Face Detection
            results = face_detection.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

            # Draw face detections of each face.
            if not results.detections:
                return img, [[0,0], [0]]
            annotated_image = img.copy()
            for detection in results.detections:
                print('Nose tip:')
                print(mp_face_detection.get_key_point(
                detection, mp_face_detection.FaceKeyPoint.NOSE_TIP))
                mp_drawing.draw_detection(annotated_image, detection)


    else:
        faces = []

    face_list = []
    face_area_list = []

    for (x, y, w, h) in faces:
        cv2.rectangle(img, (x,y), (x+w, y+h), (0,0,255), 2)
        cx = x + w // 2
        cy = y + h // 2
        area = w*h
        face_list.append([cx, cy])
        face_area_list.append(area)

    if len(face_list) != 0:
        i = face_area_list.index(max(face_area_list))
        return img, [face_list[i], face_area_list[i]]

    else:
        return img, [[0,0], [0]]

def webcam_findFace():
    # cap = cv2.VideoCapture(0)

    # if not cap.isOpened():
    #     print('cannot open camera')
    #     exit()

    # AREA_THRESHOLD = [25000, 30000]

    # while True:
    #     _, img = cap.read()
        
    #     img, [face_coords, area] = findFace(img)
    #     cv2.putText(img = img, text = f'{face_coords}_{area}', 
    #                 org = (30,30), fontFace = cv2.FONT_HERSHEY_SIMPLEX, 
    #                 fontScale = 1,color = (0, 0, 255), thickness = 2)
        
    #     cv2.circle(img, tuple(face_coords), 1, (255,0,0), 2,2)

    #     upper_limit = int(img.shape[0]/3)
    #     lower_limit = int(img.shape[0]/3)*2
    #     cv2.line(img, (0,int(img.shape[0]/3)),(img.shape[1], int(img.shape[0]/3)), (255, 0, 0), 1, 1)
    #     cv2.line(img, (0,int(img.shape[0]/3*2)),(img.shape[1], int(img.shape[0]/3*2)), (255, 0, 0), 1, 1)

    #     rightmost_limit = int(img.shape[1]/3)
    #     leftmost_limit =  int(img.shape[1]/3) * 2
    #     cv2.line(img, (int(img.shape[1]/3), 0),(int(img.shape[1]/3), img.shape[0]), (255, 0, 0), 1, 1)
    #     cv2.line(img, (int(img.shape[1]/3*2), 0),(int(img.shape[1]/3*2), img.shape[0]), (255, 0, 0), 1, 1)

    #     if(face_coords == [0,0]):
    #         continue
    #     else:
    #         if(face_coords[1] < upper_limit):
    #             print('down')
    #         elif(face_coords[1] > lower_limit):
    #             print('up')

    #         if(face_coords[0] < rightmost_limit):
    #             print('move_left')
    #         elif(face_coords[0] > leftmost_limit):
    #             print('move_right')

    #     if(area == 0):
    #         continue
    #     else:
    #         if(area > AREA_THRESHOLD[-1]):
    #             print('move backwards')
    #         elif(area < AREA_THRESHOLD[0]):
    #             print('move forwards')
    #         else:
    #             print('stationary')
            
    #     cv2.imshow("Output", img)

    #     press = cv2.waitKey(1)
    #     if press == ord('q'):
    #         print('Quitting')
    #         break
    cap = cv2.VideoCapture(0)
    with mp_face_detection.FaceDetection(
        model_selection=0, min_detection_confidence=0.5) as face_detection:
        while cap.isOpened():
            success, image = cap.read()
            if not success:
                print("Ignoring empty camera frame.")
                # If loading a video, use 'break' instead of 'continue'.
                continue

            # Flip the image horizontally for a later selfie-view display, and convert
            # the BGR image to RGB.
            image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
            # To improve performance, optionally mark the image as not writeable to
            # pass by reference.
            image.flags.writeable = False
            results = face_detection.process(image)

            # Draw the face detection annotations on the image.
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            if results.detections:
                for detection in results.detections:
                    mp_drawing.draw_detection(image, detection)
                    print(mp_face_detection.get_key_point(
                        detection, mp_face_detection.FaceKeyPoint.NOSE_TIP))
                    print(mp_face_detection.get_key_point(
                        detection, mp_face_detection.FaceKeyPoint.NOSE_TIP).x)
                    print(mp_face_detection.get_key_point(
                        detection, mp_face_detection.FaceKeyPoint.NOSE_TIP).y)
                    # print(mp_face_detection.get_key_point(
                    #     detection, mp_face_detection.FaceKeyPoint.RIGHT_EYE).x)
                    # print(mp_face_detection.get_key_point(
                    #     detection, mp_face_detection.FaceKeyPoint.LEFT_EYE))

                    # cv2.putText(img = img, text = f'{face_coords}_{area}', 
                    #     org = (30,30), fontFace = cv2.FONT_HERSHEY_SIMPLEX, 
                    #     fontScale = 1,color = (0, 0, 255), thickness = 2)
                    

            cv2.imshow('MediaPipe Face Detection', image)
            if cv2.waitKey(5) & 0xFF == 27:
                break
    cap.release()

def main():
    # controls = FaceTracker()

    # run frontend
    # controls.run()
    webcam_findFace()


if __name__ == '__main__':
    main()

