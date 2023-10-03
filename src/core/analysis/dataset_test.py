import os
from torchvision.io import read_image
import numpy as np
import random

SEED = 7
random.seed(SEED)

class TestImageDataset:
    """Implement your map-style dataset class here!"""
    
    def __init__(self, transform=None, mapping=None):
        subjects = ["S9", "S11"]
        self.transform = transform
        self.frame_paths = []
        self.mapping = mapping
        
        for subject in subjects:
            subject_prefix = "/scratch/network/nobliney/project/data/preprocessed/training/" + subject + "/"
            folders = os.listdir(subject_prefix)
            for folder in folders:
                if not folder.startswith("."):
                    bbox_prefix = subject_prefix + folder
                    frames = os.listdir(bbox_prefix)
                
                    # filter out non pngs
                    frames = np.array(frames)
                    frames = frames[np.char.endswith(frames, '.png')].tolist()
                    frames = sorted(frames)
                    frames = [(bbox_prefix + "/" + frame) for frame in frames]
                
                    if len(frames) % 2 == 0:
                        self.frame_paths += frames
                        random.shuffle(frames)
                        self.frame_paths += frames
                    elif len(frames) > 2:
                        self.frame_paths += frames[:-1]
                        random.shuffle(frames)
                        self.frame_paths += frames[:-1]
        
        self.len = len(self.frame_paths) // 2
        print("Length of Dataset: ", self.len)
        print("Finished initializing dataset.")

                
    def length(self):
        return self.len

    def getitem(self, idx):
        
        frame1_path = self.frame_paths[2 * idx]
        frame1 = read_image(frame1_path)[[2,1,0],:,:]
        frame1 = frame1.div(255)
        bbox1 = self.mapping[frame1_path]['bbox']
        pose1 = self.mapping[frame1_path]['pose']
        
        frame2_path = self.frame_paths[2 * idx + 1]
        frame2 = read_image(frame2_path)[[2,1,0],:,:]
        frame2 = frame2.div(255)
        #bbox2 = self.mapping[frame2_path]['bbox']
        #pose2 = self.mapping[frame2_path]['pose']
        
        if self.transform is not None:
            frame1 = self.transform(frame1)
            frame2 = self.transform(frame2)
        
        frame1_orig_path = self.mapping[frame1_path]['path']
        #frame2_orig_path = self.mapping[frame2_path]['path']
        #return frame1, frame2, bbox1, bbox2, pose1, pose2, frame1_orig_path, frame2_orig_path
        return frame1, frame2, bbox1, pose1, frame1_orig_path

        
