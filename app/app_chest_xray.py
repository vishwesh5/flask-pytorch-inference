#!/usr/bin/env python
import os
from flask import Flask, render_template, request, send_from_directory, send_file
from flask_bootstrap import Bootstrap
import cv2

import torch, torchvision
from torchvision import datasets, models, transforms
import caffe2.python.onnx.backend as backend

import os
import onnx
from PIL import Image

import numpy as np

__author__ = 'vishwesh5'

app = Flask(__name__)
Bootstrap(app)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))

# Applying Transforms to the Data
image_transforms = {
    'train': transforms.Compose([
        transforms.RandomResizedCrop(size=256, scale=(0.8, 1.0)),
        transforms.RandomRotation(degrees=15),
        transforms.RandomHorizontalFlip(),
        transforms.CenterCrop(size=224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406],
                             [0.229, 0.224, 0.225])
    ]),
    'valid': transforms.Compose([
        transforms.Resize(size=256),
        transforms.CenterCrop(size=224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406],
                             [0.229, 0.224, 0.225])
    ]),
    'test': transforms.Compose([
        transforms.Resize(size=256),
        transforms.CenterCrop(size=224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406],
                             [0.229, 0.224, 0.225])
    ])
}

@app.route("/")
def index():
    return render_template("upload.html")

@app.route("/upload", methods=['POST'])
def upload():
    target = os.path.join('static', 'images')
    print(target)

    if not os.path.isdir(target):
        os.mkdir(target)

    for file in request.files.getlist("file"):
        print(file)
        filename = file.filename

        destination = "/".join([target, filename])
        print(destination)
        file.save(destination)
        absPath = os.path.join(APP_ROOT,destination)
        print(absPath)
        #im = cv2.imread(absPath)
        #gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

        #outputFile = "/".join([target, 'out_{}'.format(filename) ])
        #cv2.imwrite(outputFile,gray)
        model = onnx.load("../chest_xray_kaggle.onnx")
        rep = backend.prepare(model, device="CPU")
        transform = image_transforms['test']
        test_image = Image.open(absPath)
        test_image_tensor = transform(test_image)
        print(test_image_tensor.shape)
        if torch.cuda.is_available():
            test_image_tensor = test_image_tensor.view(1, 1, 224, 224).cuda()
        else:
            test_image_tensor = test_image_tensor.view(1, 1, 224, 224)
        np_image = test_image_tensor.numpy()
        outputs = rep.run(np_image.astype(np.float32))
        ps = torch.exp(torch.from_numpy(outputs[0]))
        topk, topclass = ps.topk(2, dim=1)
        out_img = cv2.imread("./static/images/blank_output.png")
        for i in range(2):
            print("Predcition", i+1, ":", topclass[0][i], ", Score: ", topk[0][i].item())
            data_to_write = "Prediction %d: %d, Score: %.3f"%(i,topclass[0][i],topk[0][i].item())
            out_img = cv2.putText(out_img, data_to_write,
                    (70,100+200*i),cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,0),2,cv2.LINE_AA)
        outputFile = "/".join([target, 'out_{}'.format(filename) ])
        cv2.imwrite(outputFile,out_img)
    # return send_from_directory("images", filename, as_attachment=True)
    return render_template("complete.html", input=filename , output=outputFile)

@app.route('/<filename>')
def send_image(filename):
    print(filename)
    return send_from_directory("static/images", filename)

if __name__ == "__main__":
    app.run(port=4555, debug=True)
