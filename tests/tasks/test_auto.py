import warnings
from pathlib import Path

from flash.image import ImageClassificationData, ImageClassifier

from gradsflow.autotasks import autotask

warnings.filterwarnings("ignore")

data_dir = Path.cwd()
datamodule = ImageClassificationData.from_folders(
    train_folder=f"{data_dir}/data/hymenoptera_data/train/",
    val_folder=f"{data_dir}/data/hymenoptera_data/val/",
)


def test_build_model():
    model = autotask(
        task="image",
        datamodule=datamodule,
        max_epochs=1,
        timeout=5,
        suggested_backbones="ssl_resnet18",
        n_trials=1,
    )
    kwargs = {"backbone": "ssl_resnet18", "optimizer": "adam", "lr": 1e-1}
    model.model = model.build_model(kwargs)
    assert isinstance(model.model, ImageClassifier)


def test_hp_tune():
    model = autotask(
        task="image",
        datamodule=datamodule,
        max_epochs=1,
        max_steps=2,
        timeout=30,
        suggested_backbones="ssl_resnet18",
        optimization_metric="val_accuracy",
        n_trials=1,
    )
    model.hp_tune(
        name="my-experiment", mode="max", gpu=0, trainer_config={"fast_dev_run": True}
    )
