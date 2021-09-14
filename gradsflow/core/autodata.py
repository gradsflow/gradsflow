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
from typing import Optional

import pytorch_lightning as pl
from loguru import logger


class AutoDataset:
    def __init__(
        self,
        train_dataloader: Optional = None,
        val_dataloader: Optional = None,
        datamodule: Optional[pl.LightningDataModule] = None,
        num_classes: Optional[int] = None,
    ):

        self.datamodule = None
        self.num_classes = num_classes

        if not (datamodule or train_dataloader):
            raise UserWarning("Both datamodule and train_dataloader can't be None!")

        if all((datamodule, train_dataloader)):
            logger.warning(
                "Both datamodule and train_dataloader is set!"
                "Using datamodule over train_dataloader."
            )

        if not datamodule:
            datamodule = pl.LightningDataModule()
            datamodule.train_dataloader = train_dataloader
            datamodule.val_dataloader = val_dataloader
            datamodule.num_classes = num_classes

        if datamodule:
            self.datamodule = datamodule
            if hasattr(datamodule, "num_classes"):
                num_classes = datamodule.num_classes
            if num_classes is None:
                raise UserWarning("num_classes is None!")

        self.datamodule = datamodule
        self.num_classes = num_classes