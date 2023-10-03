import torch
import kornia
import argparse
import torchvision.transforms as T
from old_networks import ParameterRegressor
from src.core.utils.helper import draw_template, load_anchor_points
from src.core.utils.transforms import transform_template, transform_anchor_points

class Predictor:
    def __init__(self, batch_size, num_parts, device, template_path, anchors_path):
        self.I = torch.Tensor([[1, 0, 0], [0, 1, 0]]).view(1, 1, 2, 3).repeat(batch_size, num_parts, 1, 1).to(device)
        self.aug = torch.Tensor([0, 0, 1]).view(1, 1, 1, 3).repeat(batch_size, num_parts, 1, 1).to(device)
        self.net = ParameterRegressor(n_f=32, num_joints=num_parts).to(device)
        self.template = draw_template(template_path, size=256, batch_size=batch_size, device=device)
        self.core, self.single, self.double = load_anchor_points(anchors_path, device, batch_size)
        self.net = self.net.eval()
        # reorder the parts/anchors from old to new ordering
        self.indices = [0, 1, 2, 3, 4, 11, 12, 5, 6, 7, 8, 9, 10, 13, 14, 15, 16, 17]
        self.device = device

    def load_checkpoint(self, path):
        self.net.load_state_dict(torch.load(path)['regressor_network'], strict=False)

    def transform(self, template, params):
        # translation should be in range from 0 to roughly 1, so scale up here
        # params[:, 0:3, -1] = params[..., -1] * 256
        params[:, 0:3, -1] = params[:, 0:3, -1] * 256
        warped_template = kornia.geometry.affine(template, params, align_corners = False)
        return warped_template

    def predict(self, frame):
        """
        frame: shape [b, 3 (bgr), height, width], to normalize run
        normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225])
        totensor = transforms.ToTensor()
        transform = transforms.Compose([totensor, normalize])
        """
        
        params, _ = self.net(frame, self.template)
        params = self.I + params
        params = params[:, self.indices]

        batched_params = params.view(-1, 2, 3)
        batched_template = self.template.view(-1, 256, 256).unsqueeze(1)
        warped_heatmaps = transform_template(batched_template, batched_params) # estimated warped template
        #warped_heatmaps = self.transform(batched_template, batched_params)
        
        
        A = torch.cat([params, self.aug], dim=-2)
        transformed_anchors = transform_anchor_points(A, self.core, self.double, self.single)

        warped_heatmaps = warped_heatmaps.view(-1, 18, 256, 256)
        
        return warped_heatmaps, transformed_anchors
