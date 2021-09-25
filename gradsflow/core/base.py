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
from abc import ABC, abstractmethod
from typing import Dict, List, Union

import torch
from torch import nn

from gradsflow.core.autodata import AutoDataset
from gradsflow.core.callbacks import ComposeCallback, Tracker
from gradsflow.utility.common import listify, module_to_cls_index


class BaseAutoModel(ABC):
    """
    The main class for AutoML which consists everything required for tranining a model -
    data, model and trainer.
    """

    _OPTIMIZER_INDEX = module_to_cls_index(torch.optim, True)

    @abstractmethod
    def _create_search_space(self) -> Dict[str, str]:
        """creates search space"""
        raise NotImplementedError

    @abstractmethod
    def build_model(self, search_space: dict) -> torch.nn.Module:
        """Build model from dictionary search_space"""
        raise NotImplementedError

    def fit(
        self,
        auto_data: AutoDataset,
        search_space: dict,
        epochs=1,
        callbacks: Union[List, None] = None,
    ):
        """
        Similar to Keras model.fit() it trains the model for specified epochs and returns Tracker object
        Args:
            auto_data: AutoDataset object encapsulate dataloader and datamodule
            search_space:
            epochs:
            callbacks:

        Returns:

        """
        callbacks = listify(callbacks)
        device = "cpu"
        if torch.cuda.is_available():
            device = "cuda"

        train_dataloader = auto_data.train_dataloader
        val_dataloader = auto_data.val_dataloader

        model = self.build_model(search_space).to(device)
        optimizer_fn = self._OPTIMIZER_INDEX[search_space["optimizer"]]
        optimizer = optimizer_fn(model.parameters(), lr=search_space["lr"])

        criterion = nn.CrossEntropyLoss()

        tracker = Tracker()
        tracker.model = model
        tracker.optimizer = optimizer
        callbacks = ComposeCallback(tracker, *callbacks)

        # ----- EVENT: ON_TRAINING_START
        callbacks.on_training_start()

        for epoch in range(epochs):  # loop over the dataset multiple times
            tracker.epoch = epoch
            tracker.running_loss = 0.0
            tracker.epoch_steps = 0
            tracker.train_loss = 0.0
            tracker.train_steps = 0

            # ----- EVENT: ON_EPOCH_START
            callbacks.on_epoch_start()

            for i, data in enumerate(train_dataloader, 0):
                # get the inputs; data is a list of [inputs, labels]
                inputs, labels = data
                inputs, labels = inputs.to(device), labels.to(device)

                # zero the parameter gradients
                optimizer.zero_grad()

                # forward + backward + optimize
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()

                # print statistics
                tracker.running_loss += loss.item()
                tracker.train_loss += loss.item()
                tracker.epoch_steps += 1
                tracker.train_steps += 1
                if i % 100 == 0:  # print every 100 mini-batches
                    print(
                        f"epoch: {epoch}, loss: {tracker.running_loss / tracker.epoch_steps :.3f}"
                    )
                    tracker.running_loss = 0.0

            # END OF TRAIN EPOCH
            tracker.train_loss /= tracker.train_steps + 1e-9

            # Validation loss
            tracker.val_loss = 0.0
            tracker.val_steps = 0
            tracker.total = 0
            tracker.correct = 0
            for i, data in enumerate(val_dataloader, 0):
                with torch.no_grad():
                    inputs, labels = data
                    inputs, labels = inputs.to(device), labels.to(device)

                    outputs = model(inputs)
                    _, predicted = torch.max(outputs.data, 1)
                    tracker.total += labels.size(0)
                    tracker.correct += (predicted == labels).sum().item()

                    loss = criterion(outputs, labels)
                    tracker.val_loss += loss.cpu().numpy()
                    tracker.val_steps += 1
            tracker.val_loss /= tracker.val_steps + 1e-9
            tracker.val_accuracy = tracker.correct / tracker.val_steps

            print(
                f"epoch {tracker.epoch}: train/loss={tracker.train_loss}, "
                f"val/loss={tracker.val_loss}, val/accuracy={tracker.val_accuracy}"
            )

            # ----- EVENT: ON_EPOCH_END
            callbacks.on_epoch_end()

        # ----- EVENT: ON_TRAINING_END
        callbacks.on_epoch_end()

        print("Finished Training")
        return tracker
