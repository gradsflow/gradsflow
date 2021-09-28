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

import os
from typing import Any, Dict, List, Optional, Union

import torch
from rich.progress import BarColumn, Progress, RenderableColumn, TimeRemainingColumn
from torch import nn

from gradsflow.core.callbacks import Callback, ComposeCallback
from gradsflow.core.data import AutoDataset
from gradsflow.models.base import BaseModel
from gradsflow.models.tracker import Tracker
from gradsflow.utility.common import listify, module_to_cls_index


class Model(BaseModel):
    TEST = os.environ.get("GF_CI", "false").lower() == "true"
    _OPTIMIZER_INDEX = module_to_cls_index(torch.optim, True)

    def __init__(
        self,
        learner: Union[nn.Module, Any],
        accelerator_config: dict = None,
    ):
        accelerator_config = accelerator_config or {}
        super().__init__(learner=learner, accelerator_config=accelerator_config)

        self.criterion = nn.CrossEntropyLoss()
        self.tracker = Tracker()
        self.tracker.learner = self.learner

    def train_step(self, inputs: torch.Tensor, target: torch.Tensor) -> Dict[str, torch.Tensor]:
        self.optimizer.zero_grad()
        logits = self.learner(inputs)
        loss = self.loss(logits, target)
        self.accelerator.backward(loss)
        self.optimizer.step()
        return {"loss": loss, "logits": logits}

    def val_step(self, inputs: torch.Tensor, target: torch.Tensor) -> Dict[str, torch.Tensor]:
        logits = self.learner(inputs)
        loss = self.criterion(logits, target)
        _, predictions = torch.max(logits.data, 1)

        return {"loss": loss, "logits": logits, "predictions": predictions}

    def train_epoch(self, autodataset):
        train_dataloader = autodataset.train_dataloader
        tracker = self.tracker
        running_train_loss = 0.0
        tracker.train.steps = 0
        steps_per_epoch = tracker.steps_per_epoch

        tracker.train_prog = tracker.progress.add_task("[green]Learning...", total=len(train_dataloader))
        self.learner.train()
        for step, (inputs, labels) in enumerate(train_dataloader):
            inputs, labels = inputs.to(self.device), labels.to(self.device)
            outputs = self.train_step(inputs, labels)
            loss = outputs["loss"].item()
            running_train_loss += loss
            tracker.train.steps += 1
            tracker.progress.update(tracker.train_prog, advance=1)

            if self.TEST:
                break
            if steps_per_epoch and step >= steps_per_epoch:
                break
        tracker.train.loss = running_train_loss / (tracker.train.steps + 1e-9)
        tracker.progress.remove_task(tracker.train_prog)

    def val_epoch(self, autodataset):
        if not autodataset.val_dataloader:
            return
        val_dataloader = autodataset.val_dataloader
        tracker = self.tracker
        tracker.total = 0
        tracker.correct = 0
        running_val_loss = 0.0
        tracker.val.steps = 0

        val_prog = tracker.progress.add_task("[green]Validating...", total=len(val_dataloader))
        self.learner.eval()
        for _, (inputs, labels) in enumerate(val_dataloader):
            with torch.no_grad():
                inputs, labels = inputs.to(self.device), labels.to(self.device)
                outputs = self.val_step(inputs, labels)
                loss = outputs["loss"]
                predicted = outputs["predictions"]
                tracker.total += labels.size(0)
                tracker.correct += (predicted == labels).sum().item()
                running_val_loss += loss.cpu().numpy()
                tracker.val.steps += 1
                tracker.progress.update(val_prog, advance=1)
            if self.TEST:
                break
        tracker.val.loss = running_val_loss / (tracker.val.steps + 1e-9)
        tracker.tune_metric = tracker.val_accuracy = tracker.correct / tracker.val.steps
        tracker.progress.remove_task(val_prog)

    def fit(
        self,
        autodataset: AutoDataset,
        epochs: int = 1,
        steps_per_epoch: Optional[int] = None,
        callbacks: Union[List[str], Callback] = None,
        resume: bool = True,
        progress_kwargs: Optional[Dict] = None,
    ) -> Tracker:
        """
        Similar to Keras model.fit() it trains the model for specified epochs and returns Tracker object
        Args:
            autodataset: AutoDataset object encapsulate dataloader and datamodule
            epochs: number of epochs to train
            steps_per_epoch: Number of steps trained in a single epoch
            callbacks: Callback object or string
            resume: Resume training from the last epoch
            progress_kwargs: Arguments for rich.progress

        Returns:
            Tracker object
        """
        self.assert_compiled()
        optimizer = self.optimizer
        progress_kwargs = progress_kwargs or {}
        composed_callbacks: ComposeCallback = ComposeCallback(self.tracker, *listify(callbacks))

        autodataset.train_dataloader, autodataset.val_dataloader = self.accelerator.prepare(
            autodataset.train_dataloader, autodataset.val_dataloader
        )

        if not resume:
            self.tracker.reset()
        tracker = self.tracker
        tracker.max_epochs = epochs
        tracker.optimizer = optimizer
        tracker.steps_per_epoch = steps_per_epoch

        # ----- EVENT: ON_TRAINING_START
        composed_callbacks.on_training_start()

        bar_column = BarColumn()
        table_column = RenderableColumn(tracker.create_table())

        progress = Progress(
            "[progress.description]{task.description}",
            bar_column,
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeRemainingColumn(),
            table_column,
            expand=True,
            **progress_kwargs,
        )
        tracker.progress = progress
        with progress:
            epoch_prog = progress.add_task("[red]Epoch Progress...", total=epochs, completed=tracker.epoch)

            for epoch in range(tracker.epoch, epochs):
                tracker.epoch = epoch

                # ----- EVENT: ON_EPOCH_START
                composed_callbacks.on_epoch_start()
                self.train_epoch(autodataset)
                table_column.renderable = tracker.create_table()

                # END OF TRAIN EPOCH
                self.val_epoch(autodataset)
                table_column.renderable = tracker.create_table()

                # ----- EVENT: ON_EPOCH_END
                composed_callbacks.on_epoch_end()
                progress.update(epoch_prog, advance=1)

                if self.TEST:
                    break

        # ----- EVENT: ON_TRAINING_END
        composed_callbacks.on_training_end()

        return tracker