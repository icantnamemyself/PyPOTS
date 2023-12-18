"""

"""

# Created by Wenjie Du <wenjay.du@gmail.com>
# License: BSD-3-Clause

from typing import Union, Iterable

import torch
from pygrinder import mcar

from ...data.base import BaseDataset


class DatasetForCSDI(BaseDataset):
    """Dataset for CSDI model."""

    def __init__(
        self,
        data: Union[dict, str],
        return_labels: bool = True,
        file_type: str = "h5py",
        rate: float = 0.1,
    ):
        super().__init__(data, return_labels, file_type)
        self.rate = rate

    def _fetch_data_from_array(self, idx: int) -> Iterable:
        """Fetch data according to index.

        Parameters
        ----------
        idx : int,
            The index to fetch the specified sample.

        Returns
        -------
        sample : list,
            A list contains

            index : int tensor,
                The index of the sample.

            X_intact : tensor,
                Original time-series for calculating mask imputation loss.

            X : tensor,
                Time-series data with artificially missing values for model input.

            missing_mask : tensor,
                The mask records all missing values in X.

            indicating_mask : tensor.
                The mask indicates artificially missing values in X.
        """
        X = self.X[idx].to(torch.float32)
        X_intact, X, missing_mask, indicating_mask = mcar(X, p=self.rate)

        observed_data = X_intact
        observed_mask = missing_mask + indicating_mask
        gt_mask = missing_mask
        observed_tp = (
            torch.arange(0, self.n_steps, dtype=torch.float32)
            if "time_points" not in self.data.keys()
            else torch.from_numpy(self.data["time_points"][idx]).to(torch.float32)
        )
        for_pattern_mask = (
            gt_mask
            if "for_pattern_mask" not in self.data.keys()
            else torch.from_numpy(self.data["for_pattern_mask"][idx]).to(torch.float32)
        )
        cut_length = (
            torch.zeros(len(observed_data)).long()
            if "cut_length" not in self.data.keys()
            else torch.from_numpy(self.data["cut_length"][idx]).to(torch.float32)
        )

        sample = [
            torch.tensor(idx),
            observed_data,
            observed_mask,
            observed_tp,
            gt_mask,
            for_pattern_mask,
            cut_length,
        ]

        if self.y is not None and self.return_labels:
            sample.append(self.y[idx].to(torch.long))

        return sample

    def _fetch_data_from_file(self, idx: int) -> Iterable:
        """Fetch data with the lazy-loading strategy, i.e. only loading data from the file while requesting for samples.
        Here the opened file handle doesn't load the entire dataset into RAM but only load the currently accessed slice.

        Parameters
        ----------
        idx : int,
            The index of the sample to be return.

        Returns
        -------
        sample : list,
            The collated data sample, a list including all necessary sample info.
        """

        if self.file_handle is None:
            self.file_handle = self._open_file_handle()

        X = torch.from_numpy(self.file_handle["X"][idx]).to(torch.float32)
        X_intact, X, missing_mask, indicating_mask = mcar(X, p=self.rate)

        observed_data = X_intact
        observed_mask = missing_mask + indicating_mask
        gt_mask = indicating_mask
        observed_tp = (
            torch.arange(0, self.n_steps, dtype=torch.float32)
            if "time_points" not in self.file_handle.keys()
            else torch.from_numpy(self.file_handle["time_points"][idx]).to(
                torch.float32
            )
        )
        for_pattern_mask = (
            gt_mask
            if "for_pattern_mask" not in self.file_handle.keys()
            else torch.from_numpy(self.file_handle["for_pattern_mask"][idx]).to(
                torch.float32
            )
        )
        cut_length = (
            torch.zeros(len(observed_data)).long()
            if "cut_length" not in self.file_handle.keys()
            else torch.from_numpy(self.file_handle["cut_length"][idx]).to(torch.float32)
        )

        sample = [
            torch.tensor(idx),
            observed_data,
            observed_mask,
            observed_tp,
            gt_mask,
            for_pattern_mask,
            cut_length,
        ]

        # if the dataset has labels and is for training, then fetch it from the file
        if "y" in self.file_handle.keys() and self.return_labels:
            sample.append(torch.tensor(self.file_handle["y"][idx], dtype=torch.long))

        return sample