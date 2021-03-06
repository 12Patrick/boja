import os
from typing import List

from PIL import Image
import torch

from .pascal_voc_parser import read_content, has_boxes
from .transforms import ToTensor, RandomHorizontalFlip, Compose


INVALID_ANNOTATION_FILE_IDENTIFIER = "invalid"


class BojaDataSet(object):
    def __init__(
        self,
        image_dir_path: str,
        annotation_dir_path: str,
        manifest_file_path: str,
        labels: List[str],
        training: bool = False,
    ):
        self.image_dir_path = image_dir_path
        self.annotation_dir_path = annotation_dir_path

        self.transforms = self.get_transforms(training)

        self.labels = labels
        manifest_items = [
            item.strip() for item in open(manifest_file_path).read().splitlines()
        ]
        # Filter out Invalid images and annotations with no bounding boxes, ensure files exist
        manifest_items = [
            item
            for item in manifest_items
            if os.path.isfile(os.path.join(self.image_dir_path, item.split(",")[0]))
            and os.path.isfile(
                os.path.join(self.annotation_dir_path, item.split(",")[1])
            )
            and item.split(",")[1].lower() != INVALID_ANNOTATION_FILE_IDENTIFIER
            and has_boxes(os.path.join(self.annotation_dir_path, item.split(",")[1]))
        ]

        self.images = [
            os.path.join(self.image_dir_path, item.split(",")[0])
            for item in manifest_items
        ]
        self.annotations = [
            os.path.join(self.annotation_dir_path, item.split(",")[1])
            for item in manifest_items
        ]

    def __getitem__(self, idx):
        # load images ad masks
        img = Image.open(self.images[idx]).convert("RGB")
        _, annotation_boxes = read_content(self.annotations[idx])

        num_objs = len(annotation_boxes)
        boxes = [[b.xmin, b.ymin, b.xmax, b.ymax] for b in annotation_boxes]
        boxes = torch.as_tensor(boxes, dtype=torch.float32)
        # there is only one class

        labels = [self.labels.index(b.label) for b in annotation_boxes]
        labels = torch.as_tensor(labels, dtype=torch.int64)

        image_id = torch.tensor([idx])  # pylint: disable=not-callable

        area = [b.get_area() for b in annotation_boxes]
        area = torch.as_tensor(area, dtype=torch.float32)

        # suppose all instances are not crowd
        iscrowd = torch.zeros((num_objs,), dtype=torch.int64)

        target = {}
        target["boxes"] = boxes
        target["labels"] = labels
        target["image_id"] = image_id
        target["area"] = area
        target["iscrowd"] = iscrowd

        if self.transforms is not None:
            img, target = self.transforms(img, target)

        return img, target

    def get_transforms(self, train):
        transforms = []
        transforms.append(ToTensor())
        if train:
            transforms.append(RandomHorizontalFlip(0.5))
        return Compose(transforms)

    def __len__(self):
        return len(self.images)

