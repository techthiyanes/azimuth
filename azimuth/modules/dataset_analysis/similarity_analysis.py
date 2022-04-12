# Copyright ServiceNow, Inc. 2021 – 2022
# This source code is licensed under the Apache 2.0 license found in the LICENSE file
# in the root directory of this source tree.
import itertools
from collections import defaultdict
from os.path import join as pjoin
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
from datasets import Dataset
from filelock import FileLock
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from azimuth.config import SimilarityConfig, SimilarityOptions
from azimuth.dataset_split_manager import FEATURE_FAISS, DatasetSplitManager
from azimuth.modules.base_classes.indexable_module import (
    DatasetResultModule,
    IndexableModule,
)
from azimuth.modules.task_execution import get_task_result
from azimuth.types.general.array_type import Array
from azimuth.types.general.dataset import DatasetColumn, DatasetSplitName
from azimuth.types.general.module_options import ModuleOptions
from azimuth.types.similarity_analysis import FAISSResponse
from azimuth.types.tag import SmartTag, TaggingResponse
from azimuth.utils.validation import assert_not_none

NUM_NEIGHBORS = 20


class FAISSModule(IndexableModule[SimilarityConfig]):
    """Compute the FAISS features for a dataset split."""

    def __init__(
        self,
        dataset_split_name: DatasetSplitName,
        config: SimilarityConfig,
        mod_options: Optional[ModuleOptions] = None,
    ):
        self.encoder = None
        super().__init__(dataset_split_name, config, mod_options)

    def get_model(self):
        if self.encoder is None:
            with FileLock(pjoin(self.cache_dir, "st.lock")):
                self.encoder = SentenceTransformer(self.config.similarity.faiss_encoder)
        return self.encoder

    def compute_on_dataset_split(self) -> List[FAISSResponse]:  # type: ignore
        ds = self.get_dataset_split()
        encoder = self.get_model()

        encoded = encoder.encode(
            ds[self.config.columns.text_input],
            batch_size=self.config.batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,
        )
        self.encoder = None
        torch.cuda.empty_cache()
        self.get_dataset_split_manager().add_faiss_index(encoded.astype(np.float32))
        return [FAISSResponse(features=f) for f in encoded]

    def compute(self, batch: Dataset):
        raise NotImplementedError


class NeighborsTaggingModule(DatasetResultModule[SimilarityConfig]):
    """Compute neighbors for each utterance in a dataset split."""

    def compute_on_dataset_split(self) -> List[TaggingResponse]:  # type: ignore
        if DatasetSplitName.train in self.available_dataset_splits:
            train_dm: Optional[DatasetSplitManager] = self.get_dataset_split_manager(
                DatasetSplitName.train
            )
            # NOTE: Doing this ensure that the FAISS index exists somewhere.
            # If FAISSModule fails this module will fail instead of blocking.
            train_features: Optional[List[Array]] = self._get_features(DatasetSplitName.train)
        else:
            train_dm = None
            train_features = None

        eval_dm = self.get_dataset_split_manager(DatasetSplitName.eval)
        eval_features = self._get_features(DatasetSplitName.eval)
        ds_features = assert_not_none(
            eval_features if self.dataset_split_name == DatasetSplitName.eval else train_features
        )

        indices = self.get_indices()
        neighbors = self.get_neighbors([ds_features[i] for i in indices])

        similarity_config: SimilarityOptions = assert_not_none(self.config.similarity)
        dm = assert_not_none(
            eval_dm if self.dataset_split_name == DatasetSplitName.eval else train_dm
        )

        few_similar_tags = {}
        no_close_tags = {}
        for split_name, tagname_few_similar, tagname_no_close in zip(
            [DatasetSplitName.train, DatasetSplitName.eval],
            [SmartTag.few_similar_train, SmartTag.few_similar_eval],
            [SmartTag.no_close_train, SmartTag.no_close_eval],
        ):
            if split_name not in self.available_dataset_splits:
                continue
            few_similar_tags[split_name] = self.get_few_similar_tag(
                labels=dm.get_dataset_split().select(indices)[self.config.columns.label],
                neighbors=neighbors[split_name],
                dm=self.get_dataset_split_manager(split_name),
                threshold=similarity_config.few_similar_threshold,
                tag_name=tagname_few_similar,
            )
            no_close_tags[split_name] = self.get_no_close_tag(
                neighbors=neighbors[split_name],
                threshold=similarity_config.no_close_threshold,
                tag_name=tagname_no_close,
            )

        results = []
        for (
            train_neighbors,
            eval_neighbors,
            few_similar_train,
            few_similar_eval,
            no_close_train,
            no_close_eval,
        ) in zip(
            neighbors[DatasetSplitName.train],
            neighbors[DatasetSplitName.eval],
            few_similar_tags.get(DatasetSplitName.train, []),
            few_similar_tags[DatasetSplitName.eval],
            no_close_tags[DatasetSplitName.train],
            no_close_tags[DatasetSplitName.eval],
        ):
            results.append(
                TaggingResponse(
                    tags={
                        SmartTag.few_similar_train: False
                        if few_similar_train is None
                        else few_similar_train[SmartTag.few_similar_train],
                        SmartTag.few_similar_eval: few_similar_eval[SmartTag.few_similar_eval],
                        SmartTag.no_close_train: no_close_train[SmartTag.no_close_train],
                        SmartTag.no_close_eval: no_close_eval[SmartTag.no_close_eval],
                    },
                    adds={
                        DatasetColumn.neighbors_train: train_neighbors or [],
                        DatasetColumn.neighbors_eval: eval_neighbors,
                    },
                )
            )

        return results

    def _get_features(self, ds_split_name: DatasetSplitName) -> List[Array]:
        """Get Sentence embedding features

        Args:
            ds_split_name: Name of the dataset_split to get

        Returns:
            Features for all indices.
        """
        mod = FAISSModule(
            dataset_split_name=ds_split_name,
            config=self.config,
        )
        result = get_task_result(mod, List[FAISSResponse])
        return [r.features for r in result]

    def _save_result(self, res: List[TaggingResponse], dm: DatasetSplitManager):  # type: ignore
        """Save tags for nearest neighbors.

        Args:
            res: Results from `compute_on_dataset_split`
            dm: the dataset_split manager used to get `res`.
        """
        # We don't need the key as this is not a "prediction tag"
        dm.add_tags(dict(zip(itertools.count(), (r.tags for r in res))))
        for col_name in res[0].adds.keys():
            dm.add_column(key=col_name, features=[r.adds[col_name] for r in res])

    def get_few_similar_tag(
        self,
        labels: List[int],
        neighbors: List[List[Tuple[int, float]]],
        dm: DatasetSplitManager,
        threshold: float,
        tag_name: SmartTag,
    ) -> List[Dict[SmartTag, bool]]:
        """Compute the `few_similar_train` and `few_similar_eval` tags.

        Given a list of examples, determine whether a sufficient number
         of their neighbors have the same label. If this is not the case, tag them with the
         relevant smart tag.

        Args:
            labels: List of labels per index.
            neighbors: Neighbors of each index.
            dm: DatasetSplitManager of the neighbors.
            threshold: Using this threshold to compare the ratio of items in the neighborhood
                that belong to the same class. If below this threshold, the tag will be set.
            tag_name: Name of the tag.
        """
        tags = []
        for row_label, row_neighbors in zip(labels, neighbors):
            neighbor_indices = [neighbor_idx for neighbor_idx, neighbor_similarity in row_neighbors]
            ngbr_labls = dm.get_dataset_split().select(neighbor_indices)[dm.config.columns.label]

            # Compute the ratio of neighbours with different label.
            different_labels_ratio = sum(label != row_label for label in ngbr_labls) / NUM_NEIGHBORS

            # Set the tag according to the threshold.
            tags.append({tag_name: different_labels_ratio >= threshold})
        return tags

    @staticmethod
    def get_no_close_tag(
        neighbors: List[List[Tuple[int, float]]],
        threshold: float,
        tag_name: SmartTag,
    ) -> List[Dict[SmartTag, bool]]:
        """Compute the `no_close_train` and `no_close_eval` tags.

        Given a list of examples, determine whether the nearest neighbor (class irrelevant) of
        each is farther/less than a certain similarity threshold. If so, tag it with the
        appropriate smart tag. Do this relative to neighbors in both the train and eval sets.

        Args:
            neighbors: Neighbors of each index.
            threshold: Threshold used to determine whether an example has neighbors nearby. If
            the nearest neighbor's similarity is below this threshold, the tag will be set.
            tag_name: Name of the tag.
        """
        tags = [{tag_name: row_neighbors[0][1] < threshold} for row_neighbors in neighbors]
        return tags

    def get_neighbors(
        self, features: List[Array]
    ) -> Dict[DatasetSplitName, List[List[Tuple[int, float]]]]:
        """Get neighbors in each dataset_split for all indices.

        Given a list of examples, get the NUM_NEIGHBORS closest indices.

        Args:
            features: Queries to find neighbors to.
        """

        neighbors = defaultdict(list)
        for ds_name in self.available_dataset_splits:
            dm_ = self.get_dataset_split_manager(ds_name)
            ds_tag = dm_.dataset_split_with_index()
            own_ds_name = ds_name == self.dataset_split_name
            delta = 1 if own_ds_name else 0
            for idx, query in tqdm(
                enumerate(features), desc=f"Finding neighbors in {ds_name}", total=len(features)
            ):
                # Get N + delta neighbours because it will get itself as neighbor if we are on the
                # same set.
                # TODO: Batch this with `get_nearest_examples_batch` ?
                scores, items = ds_tag.get_nearest_examples(
                    FEATURE_FAISS, query.astype(np.float32), k=NUM_NEIGHBORS + delta
                )
                neighbors[ds_name].append(
                    [
                        (i, s)
                        for i, s in zip(items[DatasetColumn.row_idx], scores)
                        if not own_ds_name or i != idx
                    ]
                )
        return neighbors
