"""
    Robot: F1
    Framework: keras
    Number of networks: 1
    Network type: None
    Predicionts:
        linear speed(v)
        angular speed(w)

"""

import numpy as np

import cv2
import time
import os
import tensorflow as tf

from utils.constants import PRETRAINED_MODELS_DIR, ROOT_PATH
from os import path
from albumentations import (
    Compose, Normalize
)
from utils.gradcam.gradcam import GradCAM

PRETRAINED_MODELS = ROOT_PATH + '/' + PRETRAINED_MODELS_DIR + 'tf_models/'


class Brain:
    """Specific brain for the f1 robot. See header."""

    def __init__(self, sensors, actuators, model=None, handler=None, config=None):
        """Constructor of the class.

        Arguments:
            sensors {robot.sensors.Sensors} -- Sensors instance of the robot
            actuators {robot.actuators.Actuators} -- Actuators instance of the robot

        Keyword Arguments:
            handler {brains.brain_handler.Brains} -- Handler of the current brain. Communication with the controller
            (default: {None})
        """
        self.motors = actuators.get_motor('motors_0')
        self.camera = sensors.get_camera('camera_0')
        self.handler = handler
        self.cont = 0
        self.inference_times = []
        self.config = config

        self.third_image = []

        if self.config['GPU'] is False:
            os.environ["CUDA_VISIBLE_DEVICES"]="-1"

        self.gpu_inference = True if tf.test.gpu_device_name() else False

        if model:
            if not path.exists(PRETRAINED_MODELS + model):
                print("File " + model + " cannot be found in " + PRETRAINED_MODELS)

            self.net = tf.keras.models.load_model(PRETRAINED_MODELS + model)
            print(self.net.summary())
        else:
            print("** Brain not loaded **")
            print("- Models path: " + PRETRAINED_MODELS)
            print("- Model: " + str(model))

    def update_frame(self, frame_id, data):
        """Update the information to be shown in one of the GUI's frames.

        Arguments:
            frame_id {str} -- Id of the frame that will represent the data
            data {*} -- Data to be shown in the frame. Depending on the type of frame (rgbimage, laser, pose3d, etc)
        """
        self.handler.update_frame(frame_id, data)

    def check_center(self, position_x):
        if (len(position_x[0]) > 1):
            x_middle = (position_x[0][0] + position_x[0][len(position_x[0]) - 1]) / 2
            not_found = False
        else:
            # The center of the line is in position 326
            x_middle = 326
            not_found = True
        return x_middle, not_found

    def get_point(self, index, img):
        mid = 0
        if np.count_nonzero(img[index]) > 0:
            left = np.min(np.nonzero(img[index]))
            right = np.max(np.nonzero(img[index]))
            mid = np.abs(left - right) / 2 + left
        return int(mid)

    def execute(self):
        """Main loop of the brain. This will be called iteratively each TIME_CYCLE (see pilot.py)"""

        self.cont += 1

        image = self.camera.getImage().data

        if self.cont == 1:
            self.first_image = image

        self.update_frame('frame_0', image)
        try:
            if self.config['ImageCropped']:
                image = image[240:480, 0:640]
            if 'ImageSize' in self.config:
                img = cv2.resize(image, (self.config['ImageSize'][0], self.config['ImageSize'][1]))
            else:
                img = image

            if self.config['ImageNormalized']:
                AUGMENTATIONS_TEST = Compose([
                    Normalize()
                ])
                image = AUGMENTATIONS_TEST(image=img)
                img = image["image"]

            if self.cont == 1:
                self.first_image_stack = img
            elif self.cont == 2:
                self.second_image_stack = img
            elif self.cont == 3:
                self.third_image_stack = img
            elif self.cont == 4:
                self.fourth_image_stack = img
            elif self.cont == 5:
                self.fifth_image_stack = img
            elif self.cont == 6:
                self.sixth_image_stack = img
            elif self.cont == 7:
                self.seventh_image_stack = img
            elif self.cont == 8:
                self.eigth_image_stack = img
            elif self.cont == 9:
                self.nineth_image_stack = img
            elif self.cont > 9:
                self.tenth_image_stack = img
                images_buffer = [self.first_image_stack, self.fifth_image_stack, self.tenth_image_stack]
                images_buffer = np.array(images_buffer)
                img = np.expand_dims(images_buffer, axis=0)

                self.first_image_stack = self.second_image_stack
                self.second_image_stack = self.third_image_stack
                self.third_image_stack = self.fourth_image_stack
                self.fourth_image_stack = self.fifth_image_stack
                self.fifth_image_stack = self.sixth_image_stack
                self.sixth_image_stack = self.seventh_image_stack
                self.seventh_image_stack = self.eigth_image_stack
                self.eigth_image_stack = self.nineth_image_stack
                self.nineth_image_stack = self.tenth_image_stack

                start_time = time.time()
                prediction = self.net.predict(img)
                self.inference_times.append(time.time() - start_time)

                if self.config['PredictionsNormalized']:
                    prediction_v = prediction[0][0] * 13
                    if prediction[0][1] >= 0.5:
                        x = prediction[0][1] - 0.5
                        prediction_w = x * 6
                    else:
                        x = 0.5 - prediction[0][1]
                        prediction_w = x * -6
                else:
                    prediction_v = prediction[0][0]
                    prediction_w = prediction[0][1]

                if prediction_w != '' and prediction_w != '':
                    self.motors.sendV(prediction_v)
                    self.motors.sendW(prediction_w)

        except Exception as err:
            print(err)