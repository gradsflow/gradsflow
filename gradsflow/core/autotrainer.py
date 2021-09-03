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
import math
from enum import Enum
from typing import Dict, Optional

import pytorch_lightning as pl
from loguru import logger
from PIL.PyAccess import logger

from gradsflow.core.callbacks import report_checkpoint_callback


class Backend(Enum):
    pl = "pl"
    torch = "torch"
    default = torch


class AutoTrainer:
    def __init__(
        self,
        datamodule,
        max_epochs: int = 10,
        max_steps: Optional[int] = None,
        backend: Optional[str] = None,
    ):
        self.backend = (backend or Backend.pl).lower()
        self.datamodule = datamodule
        self.max_epochs = max_epochs
        self.max_steps = max_steps

    # noinspection PyTypeChecker
    def lightning_objective(
        self,
        config: Dict,
        trainer_config: Dict,
        gpu: Optional[float] = 0,
    ):
        """
        Defines lightning_objective function which is used by tuner to minimize/maximize the metric.

        Args:
            config dict: key value pair of hyperparameters.
            trainer_config dict: configurations passed directly to Lightning Trainer.
            gpu Optional[float]: GPU per trial
        """
        val_check_interval = 1.0
        if self.max_steps:
            val_check_interval = max(self.max_steps - 1, 1.0)

        datamodule = self.datamodule

        trainer = pl.Trainer(
            logger=True,
            checkpoint_callback=False,
            gpus=math.ceil(gpu),
            max_epochs=self.max_epochs,
            max_steps=self.max_steps,
            callbacks=[report_checkpoint_callback()],
            val_check_interval=val_check_interval,
            **trainer_config,
        )

        model = self.build_model(config)
        hparams = dict(model=model.hparams)
        trainer.logger.log_hyperparams(hparams)
        trainer.fit(model, datamodule=datamodule)

        logger.debug(trainer.callback_metrics)
        return trainer.callback_metrics[self.optimization_metric].item()
