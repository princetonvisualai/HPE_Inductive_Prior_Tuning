################################################ Imports
OUTPUT_FILE = "analysis_best3040.txt"

def write_output(msg, mode = "a"):
    with open("progress/" + OUTPUT_FILE, "a") as f:
        f.write(msg + "\n")
    
write_output("", "w") # clear output file

write_output("Beginning updating sys path")

import sys
sys.path.append("..")
sys.path.append("../..")
sys.path.append("../../..")
sys.path.append("helper")

write_output("Finished updating sys path")

import torch
import matplotlib.pyplot as plt
import torchvision.transforms as T
import json_tricks as json

from utils.helper import load_config
from dataset_test import TestImageDataset

from helper.predict import (adjust_configs, most_recent_checkpoint, load_checkpoint, get_pose, predict_joints, sort_checkpoints)

from helper.deepdive import (dist)

plt.rcParams["savefig.bbox"] = "tight"
device = torch.device('cuda:0')

################################################ Constants
NUM_JOINTS = 15

PREFIX = "../../"
PREFIX_VOL = PREFIX + "vol/"
PREPROCESSED_TO_ORIG = PREFIX + "code/preprocessing/preprocessed_to_orig.json" # contains the file path of original frame as well
CHECKPOINTS_PREFIX = PREFIX_VOL + "checkpoints_"
TEST_SUBJECTS = ['S9', 'S11']
NORMALIZE = T.Normalize(mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225])

write_output("Beginning to fetch preprocessed_to_orig mapping.")
# Set up test dataset
# Get mapping from preprocessed frame path to corresponding bbox and pose
with open(PREPROCESSED_TO_ORIG, "r") as f:
    preprocessed_to_orig = json.load(f)

write_output("Done with fetching preprocessed_to_orig mapping.")

dataset = TestImageDataset(transform=NORMALIZE, mapping=preprocessed_to_orig)
DATASET_LENGTH = dataset.length()

write_output("Done with initializing dataset.")

################################################ Load models and configs
from models.model_mse_twostepwarp import Model as model1
from models.model_mse import Model as model2

POSTFIX1 = "mse_natural_flipaugment_twostepwarp"
POSTFIX2 = "mse_natural"

CONFIG1_YAML = POSTFIX1 + ".yaml"
CONFIG2_YAML = POSTFIX2 + ".yaml"

CHECKPOINTS_FOLDER1 = CHECKPOINTS_PREFIX + POSTFIX1 + "/"
CHECKPOINTS_FOLDER2 = CHECKPOINTS_PREFIX + POSTFIX2 + "/"

################################################

# Get configurations of both models
config1 = load_config("../../../configs/" + CONFIG1_YAML)
config2 = load_config("../../../configs/" + CONFIG2_YAML)
# train --> test configurations
adjust_configs(config1)
adjust_configs(config2)

# Instantiate both predictors
predictor1 = model1(config1, device=device)
predictor1.regressor = predictor1.regressor.eval()
predictor1.translator = predictor1.translator.eval()

predictor2 = model2(config2, device=device)
predictor2.regressor = predictor2.regressor.eval()
predictor2.translator = predictor2.translator.eval()

# Load checkpoint
INDEX1 = 10
INDEX2 = 20
checkpoint1 = sort_checkpoints(CHECKPOINTS_FOLDER1)[INDEX1 - 1]
checkpoint2 = sort_checkpoints(CHECKPOINTS_FOLDER2)[INDEX2 - 1]

"""
checkpoint1 = most_recent_checkpoint(CHECKPOINTS_FOLDER1)
checkpoint2 = most_recent_checkpoint(CHECKPOINTS_FOLDER2)
"""

load_checkpoint(predictor1, CHECKPOINTS_FOLDER1 + checkpoint1)
load_checkpoint(predictor2, CHECKPOINTS_FOLDER2 + checkpoint2)

write_output("Done with initializing models.")

##############################################################################################################

# 1. Quantitative Analysis
## 1.1 Overall Accuracy

get_midpoint = True

#pose_collection = torch.zeros(DATASET_LENGTH, NUM_JOINTS, 2, device=device)
dist1_collection = torch.zeros(DATASET_LENGTH, NUM_JOINTS, device=device)
dist2_collection = torch.zeros(DATASET_LENGTH, NUM_JOINTS, device=device)
#diagonal_collection = torch.zeros(DATASET_LENGTH, device=device)

for i in range(DATASET_LENGTH):

    if i % 10000 == 0:
        write_output("Working on {}th test frame.".format(i+1))
       
    frame1, frame2, bbox1, pose1, frame1_orig_path = dataset.getitem(i)
    
    frame1 = frame1.to(device)
    frame1 = frame1.unsqueeze(dim = 0)
    frame2 = frame2.to(device)
    frame2 = frame2.unsqueeze(dim = 0)
            
    # Scale down ground truth pose
    bbox1, pose1 = get_pose(bbox1, pose1)

    #bbox1 = torch.tensor(bbox1, device=device)
    pose1 = torch.tensor(pose1, device=device)
    
    ######## COLLECT POSE
    #pose_collection[i] = pose1
    
    # Get predicted pose
    anchors1 = predict_joints(predictor1, frame1, frame2, get_midpoint = get_midpoint)
    anchors2 = predict_joints(predictor2, frame1, frame2, get_midpoint = get_midpoint)

    anchors1 = torch.tensor(anchors1, device=device)
    anchors2 = torch.tensor(anchors2, device=device)
    
    # PDJ@0.05 = Distance between predicted and true joint < 0.05 * bbox diagonal

    #diagonal = dist(bbox1[0], bbox1[1])
    
    ######## COLLECT DIAGONAL, ERROR FROM GROUND TRUTH
    dist1_collection[i] = dist(pose1, anchors1)
    dist2_collection[i] = dist(pose1, anchors2)
    #diagonal_collection[i] = diagonal

DISTS_DIR = "dists/"

#torch.save(pose_collection, "pose_collection.pt") # NEED TO DO JUST ONCE
#torch.save(diagonal_collection, "diagonal_collection.pt") # NEED TO DO JUST ONCE

torch.save(dist1_collection, DISTS_DIR + POSTFIX1 + str(INDEX1) + ".pt")
torch.save(dist2_collection, DISTS_DIR + POSTFIX2 + str(INDEX2) + ".pt")