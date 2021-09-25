#  Copyright (c) 2021 GradsFlow. All rights reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from pathlib import Path

import timm
import torch
from flash.image import ImageClassificationData

from gradsflow.core.callbacks import Tracker
from gradsflow.core.data import AutoDataset
from gradsflow.core.model import Model

cwd = Path.cwd()
datamodule = ImageClassificationData.from_folders(
    train_folder=f"{cwd}/data/hymenoptera_data/train/",
    val_folder=f"{cwd}/data/hymenoptera_data/val/",
)

autodataset = AutoDataset(datamodule=datamodule)
cnn = timm.create_model("ssl_resnet18", pretrained=False, num_classes=2)
model = Model(cnn, "adam")
model.TEST = True


def test_predict():
    assert isinstance(model.predict(torch.randn(1, 3, 64, 64)), torch.Tensor)


def test_fit():
    tracker = model.fit(autodataset, epochs=10, steps_per_epoch=1)
    assert isinstance(tracker, Tracker)
