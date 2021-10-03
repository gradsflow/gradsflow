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
import pytest
import torch
from torch.utils.data import DataLoader, TensorDataset

from gradsflow.core.data import AutoDataset

dataset = TensorDataset(torch.randn(8, 1, 32, 32))
dataloader = DataLoader(dataset)


def test_auto_dataset():
    with pytest.raises(UserWarning):
        AutoDataset()


def test_sent_to_device():
    data = AutoDataset(dataloader)
    assert data.sent_to_device is None
    data.sent_to_device = True
    assert data.sent_to_device
