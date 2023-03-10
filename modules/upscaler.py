import os
from abc import abstractmethod

import PIL
import numpy as np
import torch
from PIL import Image
import sys
import modules.shared
from modules import modelloader, shared
from torchvision import transforms

LANCZOS = (Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
NEAREST = (Image.Resampling.NEAREST if hasattr(Image, 'Resampling') else Image.NEAREST)
from modules.paths import models_path

class Upscaler:
    name = None
    model_path = None
    model_name = None
    model_url = None
    enable = True
    filter = None
    model = None
    user_path = None
    scalers: []
    tile = True

    def __init__(self, create_dirs=False):
        self.mod_pad_h = None
        self.tile_size = 192
        self.tile_pad = 8
        self.device = modules.shared.device
        self.img = None
        self.output = None
        self.scale = 1
        self.half = not modules.shared.no_half
        self.pre_pad = 0
        self.mod_scale = None

        if self.model_path is None and self.name:
            self.model_path = os.path.join(models_path, self.name)
        if self.model_path and create_dirs:
            os.makedirs(self.model_path, exist_ok=True)

        try:
            import cv2
            self.can_tile = True
        except:
            pass

    @abstractmethod
    def do_upscale(self, img, selected_model: str):
        return img

    def upscale(self, img, scale: int, selected_model: str = None):
        self.scale = scale
        img = img.permute(0, 3, 1, 2) / 255
        if img.ndim == 4:
            dest_w = img.shape[3] * scale
            dest_h = img.shape[2] * scale
            width = img.shape[3]
            height = img.shape[2]
        else:
            dest_w = img.shape[2] * scale
            dest_h = img.shape[1] * scale
            width = img.shape[2]
            height = img.shape[1]
        for i in range(3):
            shape = (width, height)
            # (b, c, h, w)
            img = self.do_upscale(img, selected_model)
            # (b, c, h, w)
            if img.ndim == 4:
                cur_width = img.shape[3]
                cur_height = img.shape[2]
            else:
                cur_width = img.shape[2]
                cur_height = img.shape[1]
            if shape == (cur_width, cur_height):
                break

            if abs(dest_w - cur_width) <= 20 and abs(dest_h - cur_height) <=20:
                break
            
        img = (img.permute(0,2,3,1).cpu().numpy()*255).round().astype(np.uint8)
        return img
        
    @abstractmethod
    def load_model(self, path: str):
        pass

    def find_models(self, ext_filter=None) -> list:
        return modelloader.load_models(model_path=self.model_path, model_url=self.model_url, command_path=self.user_path)

    def update_status(self, prompt):
        print(f"\nextras: {prompt}", file=shared.progress_print_out)


class UpscalerData:
    name = None
    data_path = None
    scale: int = 4
    scaler: Upscaler = None
    model: None

    def __init__(self, name: str, path: str, upscaler: Upscaler = None, scale: int = 4, model=None):
        self.name = name
        self.data_path = path
        self.scaler = upscaler
        self.scale = scale
        self.model = model


class UpscalerNone(Upscaler):
    name = "None"
    scalers = []

    def load_model(self, path):
        pass

    def do_upscale(self, img, selected_model=None):
        return img

    def __init__(self, dirname=None):
        super().__init__(False)
        self.scalers = [UpscalerData("None", None, self)]


class UpscalerLanczos(Upscaler):
    scalers = []

    def do_upscale(self, img, selected_model=None):
        return img.resize((int(img.width * self.scale), int(img.height * self.scale)), resample=LANCZOS)

    def load_model(self, _):
        pass

    def __init__(self, dirname=None):
        super().__init__(False)
        self.name = "Lanczos"
        self.scalers = [UpscalerData("Lanczos", None, self)]


class UpscalerNearest(Upscaler):
    scalers = []

    def do_upscale(self, img, selected_model=None):
        return img.resize((int(img.width * self.scale), int(img.height * self.scale)), resample=NEAREST)

    def load_model(self, _):
        pass

    def __init__(self, dirname=None):
        super().__init__(False)
        self.name = "Nearest"
        self.scalers = [UpscalerData("Nearest", None, self)]