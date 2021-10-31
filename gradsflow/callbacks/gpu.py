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

from gradsflow.callbacks import Callback


class EmissionTrackerCallback(Callback):
    """
    Tracks the carbon emissions produced by deep neural networks using
    (CodeCarbon)[https://github.com/mlco2/codecarbon]. To use this callback first install codecarbon using
    `pip install codecarbon`
    """

    def __init__(self, offline: bool = False, *args, **kwargs):
        from codecarbon import EmissionsTracker, OfflineEmissionsTracker

        if offline:
            self.tracker = OfflineEmissionsTracker(*args, **kwargs)
        else:
            self.tracker = EmissionsTracker(*args, **kwargs)

        super().__init__(model=None)

    def on_epoch_start(self):
        self.tracker.start()

    def on_epoch_end(self):
        self.tracker.stop()
