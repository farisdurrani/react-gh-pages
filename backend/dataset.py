import pandas as pd
import urllib.request as request
import csv
import traceback
import torch
import torchvision.transforms as transforms
import torchvision.datasets as datasets
import os
import shutil
from enum import Enum
from torch.utils.data import DataLoader
from zipfile import ZipFile, is_zipfile
from os import mkdir, path

try:
    from backend.constants import *
except:
    from constants import *


def read_dataset(url):
    """
    Given a url to a CSV dataset, read it and build temporary csv file

    Args:
        url (str): URL to dataset
    """
    try:
        r = request.urlopen(url).read().decode("utf8").split("\n")
        reader = csv.reader(r)
        with open(CSV_FILE_PATH, mode="w", newline="") as f:
            csvwriter = csv.writer(f)
            for line in reader:
                csvwriter.writerow(line)
    except Exception as e:
        traceback.print_exc()
        raise Exception(
            "Reading Dataset from URL failed. Might want to check the validity of the URL"
        )


def read_local_csv_file(file_path):
    """
    Given a local file path or the "uploaded CSV file", read it in pandas dataframe

    Args:
        file_path (str): file path

    """
    try:
        with open(file_path, mode="r") as data_file:
            with open(CSV_FILE_PATH, mode="w", newline="") as f:
                csvwriter = csv.writer(f)
                for line in data_file:
                    csvwriter.writerow(line)
    except Exception as e:
        traceback.print_exc()
        raise Exception(
            "Reading Local CSV failed. Might want to check that you uploaded a proper CSV file"
        )


class errorMessage(Enum):
    TRAIN_AND_VALID_VOID = "The zip file doesn't contain train and valid folders"
    TRAIN_VOID = "The zip file doesn't contain train folder"
    VALID_VOID = "The zip file doesn't contain valid folder"
    NOT_ZIP = "The given file is not a zip file"
    UNEQUAL_CLASSES = "Train and valid datasets have different number of classes"
    TRAIN_NO_FILES = "Train folder has no files"
    VALID_NO_FILES = "Valid folder has no files"
    FILE_NOT_EXIST = "The file doesn't exist"
    INVALID_TRANSFORM = "The sequence of transformations is invalid"


def loader_from_zipped(
    zipped_file,
    train_transform= DEFAULT_TRANSFORM,
    valid_transform= DEFAULT_TRANSFORM,
):

    """
    Creates a dataloader from a zipped file

    Args:
        zipped_file: the file to be unzipped
        train_transform: transformer settings for the train dataset
        valid_transform: transformer setting for the validation dataset

    Returns:
        train_dataloader, valid_dataloader

    """
    if not path.exists(zipped_file):
        raise ValueError(errorMessage.FILE_NOT_EXIST.value)

    if not is_zipfile(zipped_file):
        raise ValueError(errorMessage.NOT_ZIP.value)

    if path.exists(UNZIPPED_DIR_NAME):
        shutil.rmtree(UNZIPPED_DIR_NAME)

    mkdir(UNZIPPED_DIR_NAME)
    mkdir("{}/input".format(UNZIPPED_DIR_NAME))

    files = ZipFile(zipped_file, "r")
    files.extractall("{}/input".format(UNZIPPED_DIR_NAME))
    files.close()

    def check_inside_file(dir_name):
        if not path.exists(dir_name):
            return None, None

        train_dir = None
        valid_dir = None

        for filename in os.listdir(dir_name):
            if filename == "train":
                train_dir = "{}/{}".format(dir_name, filename)
                if valid_dir is not None:
                    return train_dir, valid_dir
            elif filename == "valid":
                valid_dir = "{}/{}".format(dir_name, filename)
                if train_dir is not None:
                    return train_dir, valid_dir

        return train_dir, valid_dir
    
    def check_valid_transform(transform):
        if transform == DEFAULT_TRANSFORM:
            print("WHATTT")
            return True
        to_tensor_idx = -1
        idx = 0
        print("not default transform")
        for x in transform:
            if isinstance(x, transforms.ToTensor):
                to_tensor_idx = idx
            else:
                if to_tensor_idx == -1:
                    for y in TENSOR_ONLY_TRANSFORMS:
                        if isinstance(x, y):
                            raise ValueError(errorMessage.INVALID_TRANSFORM.value)
                else:
                    for y in PIL_ONLY_TRANSFORMS:
                        if isinstance(x, y) and to_tensor_idx != -1:
                            raise ValueError(errorMessage.INVALID_TRANSFORM.value)
            idx+=1
        print("totensorindex:", to_tensor_idx)
        if to_tensor_idx == -1:
            raise ValueError(errorMessage.INVALID_TRANSFORM.value)
        else:
            return True

    train_dir, valid_dir = check_inside_file("{}/input".format(UNZIPPED_DIR_NAME))

    name = os.path.splitext(zipped_file)[0]
    name = name.split("/")[-1]

    if not train_dir or valid_dir == None:
        train_dir, valid_dir = check_inside_file(
            "{}/input/{}".format(UNZIPPED_DIR_NAME, name)
        )

    if train_dir is None and valid_dir is None:
        shutil.rmtree(UNZIPPED_DIR_NAME)
        raise ValueError(errorMessage.TRAIN_AND_VALID_VOID.value)
    elif train_dir is None:
        shutil.rmtree(UNZIPPED_DIR_NAME)
        raise ValueError(errorMessage.TRAIN_VOID.value)
    elif valid_dir is None:
        shutil.rmtree(UNZIPPED_DIR_NAME)
        raise ValueError(errorMessage.VALID_VOID.value)

    if len(os.listdir(train_dir)) == 0:
        shutil.rmtree(UNZIPPED_DIR_NAME)
        raise ValueError(errorMessage.TRAIN_NO_FILES.value)

    if len(os.listdir(valid_dir)) == 0:
        shutil.rmtree(UNZIPPED_DIR_NAME)
        raise ValueError(errorMessage.VALID_NO_FILES.value)

    if not len(os.listdir(train_dir)) == len(os.listdir(valid_dir)):
        shutil.rmtree(UNZIPPED_DIR_NAME)
        raise ValueError(errorMessage.UNEQUAL_CLASSES.value)

    def create_transform(transform):
        print("IAM HERE")
        if len(transform) == len(DEFAULT_TRANSFORM):
            ## possibility of same array
            i = 0
            while i < len(transform):
                if transform[i] != DEFAULT_TRANSFORM[i]:
                    break
                else:
                    i += 1

            if i != len(transform):
                ## different transformation
                if check_valid_transform(transform):
                        transform = transforms.Compose([x for x in transform if x is not None])
        else:
            if check_valid_transform(transform):
                transform = transforms.Compose([x for x in transform if x is not None])
        return transform

    train_transform = create_transform(train_transform)
    valid_transform = create_transform(valid_transform)

    print(train_transform)

    train_dataset = datasets.ImageFolder(root=train_dir, transform=train_transform)
    valid_dataset = datasets.ImageFolder(root=valid_dir, transform=valid_transform)

    print(train_dataset)

    train_loader = DataLoader(train_dataset)
    valid_loader = DataLoader(valid_dataset)

    print(train_loader)

    return train_loader, valid_loader


if __name__ == "__main__":
    read_dataset("https://raw.githubusercontent.com/karkir0003/dummy/main/job.csv")
    read_local_csv_file("test.csv")

    ## local testing
    train_loader, valid_loader = loader_from_zipped("../tests/zip_files/double_zipped.Zip", train_transform=[transforms.ToTensor(),transforms.transforms.RandomChoice(transforms=[transforms.ToTensor()])])