import torch.nn as nn
import timm


class InternImageClassifier(nn.Module):
    def __init__(self, num_classes: int, pretrained: bool = True,
                 drop_path_rate: float = 0.1, drop_rate: float = 0.0):
        super().__init__()

        self.backbone = timm.create_model(
            'convnext_tiny',
            pretrained=pretrained,
            num_classes=0,
            drop_path_rate=drop_path_rate,
        )

        self.feature_dim = self.backbone.num_features

        self.global_context = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(self.feature_dim, self.feature_dim // 4, 1),
            nn.GELU(),
            nn.Conv2d(self.feature_dim // 4, self.feature_dim, 1),
            nn.Sigmoid()
        )

        self.head = nn.Sequential(
            nn.LayerNorm(self.feature_dim),
            nn.Dropout(max(drop_rate, 0.1)),
            nn.Linear(self.feature_dim, num_classes)
        )

    def forward(self, x):
        features = self.backbone.forward_features(x)

        context = self.global_context(features)
        features = features * context

        x = features.mean(dim=[-2, -1])

        return self.head(x)
