# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import builtins
import os
from pathlib import Path
from typing import Any, Generator

import pytest
import torch
import torch.nn as nn
from _pytest.fixtures import SubRequest
from _pytest.monkeypatch import MonkeyPatch

from torchgeo.datasets import So2Sat, So2SatDataModule

pytest.importorskip("h5py")


class TestSo2Sat:
    @pytest.fixture(params=["train", "validation", "test"])
    def dataset(
        self, monkeypatch: Generator[MonkeyPatch, None, None], request: SubRequest
    ) -> So2Sat:
        md5s = {
            "train": "086c5fa964a401d4194d09ab161c39f1",
            "validation": "dd864f1af0cd495af99d7de80103f49e",
            "test": "320102c5c15f3cee7691f203824028ce",
        }

        monkeypatch.setattr(So2Sat, "md5s", md5s)  # type: ignore[attr-defined]
        root = os.path.join("tests", "data", "so2sat")
        split = request.param
        transforms = nn.Identity()  # type: ignore[attr-defined]
        return So2Sat(root, split, transforms, checksum=True)

    @pytest.fixture
    def mock_missing_module(
        self, monkeypatch: Generator[MonkeyPatch, None, None]
    ) -> None:
        import_orig = builtins.__import__

        def mocked_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "h5py":
                raise ImportError()
            return import_orig(name, *args, **kwargs)

        monkeypatch.setattr(  # type: ignore[attr-defined]
            builtins, "__import__", mocked_import
        )

    def test_getitem(self, dataset: So2Sat) -> None:
        x = dataset[0]
        assert isinstance(x, dict)
        assert isinstance(x["image"], torch.Tensor)
        assert isinstance(x["label"], int)

    def test_len(self, dataset: So2Sat) -> None:
        assert len(dataset) == 10

    def test_out_of_bounds(self, dataset: So2Sat) -> None:
        # h5py at version 2.10.0 raises a ValueError instead of an IndexError so we
        # check for both here
        with pytest.raises((IndexError, ValueError)):
            dataset[10]

    def test_invalid_split(self) -> None:
        with pytest.raises(AssertionError):
            So2Sat(split="foo")

    def test_not_downloaded(self, tmp_path: Path) -> None:
        with pytest.raises(RuntimeError, match="Dataset not found or corrupted."):
            So2Sat(str(tmp_path))

    def test_mock_missing_module(
        self, dataset: So2Sat, mock_missing_module: None
    ) -> None:
        with pytest.raises(
            ImportError,
            match="h5py is not installed and is required to use this dataset",
        ):
            So2Sat(dataset.root)


class TestSo2SatDataModule:
    @pytest.fixture(scope="class", params=zip([True, False], ["rgb", "s2"]))
    def datamodule(self, request: SubRequest) -> So2SatDataModule:
        unsupervised_mode, bands = request.param
        root = os.path.join("tests", "data", "so2sat")
        batch_size = 2
        num_workers = 0
        dm = So2SatDataModule(root, batch_size, num_workers, bands, unsupervised_mode)
        dm.prepare_data()
        dm.setup()
        return dm

    def test_train_dataloader(self, datamodule: So2SatDataModule) -> None:
        next(iter(datamodule.train_dataloader()))

    def test_val_dataloader(self, datamodule: So2SatDataModule) -> None:
        next(iter(datamodule.val_dataloader()))

    def test_test_dataloader(self, datamodule: So2SatDataModule) -> None:
        next(iter(datamodule.test_dataloader()))
