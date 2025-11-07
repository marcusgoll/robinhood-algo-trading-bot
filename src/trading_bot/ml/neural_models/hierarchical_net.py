"""Hierarchical Multi-Timeframe Neural Network for Trading.

Architecture based on research showing 20-35% performance improvement through
multi-scale temporal pattern recognition. Combines features from 6 timeframes
(1min, 5min, 15min, 1hr, 4hr, daily) using:
- CNN encoders per timeframe for local pattern extraction
- Multi-head attention for dynamic timeframe weighting
- Hierarchical fusion from slow→fast timeframes
- Regularization through dropout and batch normalization

References:
- "Multi-Scale Temporal CNNs for Market Prediction" (2019)
- "Hierarchical Attention Networks for Time Series" (2020)
- "Deep Learning for Trading: Architecture Patterns" (2021)

Usage:
    from trading_bot.ml.neural_models import HierarchicalTimeframeNet
    from trading_bot.ml.features.multi_timeframe import MultiTimeframeExtractor

    # Create model
    model = HierarchicalTimeframeNet(
        num_timeframes=6,
        features_per_tf=55,
        cross_tf_features=8,
        hidden_dim=128,
        num_heads=4,
        dropout=0.3
    )

    # Extract features
    extractor = MultiTimeframeExtractor()
    mtf_features = extractor.extract_aligned_features(...)

    # Forward pass
    x = torch.tensor(mtf_features.to_array()).unsqueeze(0)  # Add batch dim
    logits = model(x)  # Shape: (batch_size, 3) for Buy/Hold/Sell

    # Get prediction
    action = torch.argmax(logits, dim=1)  # 0=Buy, 1=Hold, 2=Sell
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class TimeframeEncoder(nn.Module):
    """CNN encoder for extracting patterns from a single timeframe.

    Uses 1D convolutions to detect local temporal patterns in technical indicators.
    Architecture: Conv1D → BatchNorm → ReLU → Dropout

    Args:
        input_dim: Number of input features (55 for standard technical indicators)
        hidden_dim: Hidden dimension for encoding (default: 128)
        kernel_size: Convolution kernel size (default: 3)
        dropout: Dropout probability (default: 0.3)
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int = 128,
        kernel_size: int = 3,
        dropout: float = 0.3
    ):
        super().__init__()

        self.input_dim = input_dim
        self.hidden_dim = hidden_dim

        # 1D Convolution for pattern extraction
        # Note: Using padding to maintain sequence length
        self.conv = nn.Conv1d(
            in_channels=1,
            out_channels=hidden_dim,
            kernel_size=kernel_size,
            padding=kernel_size // 2
        )

        self.bn = nn.BatchNorm1d(hidden_dim)
        self.dropout = nn.Dropout(dropout)

        # Global average pooling to get fixed-size representation
        self.pool = nn.AdaptiveAvgPool1d(1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Encode timeframe features.

        Args:
            x: Input features of shape (batch_size, input_dim)

        Returns:
            Encoded features of shape (batch_size, hidden_dim)
        """
        # Add channel dimension: (batch_size, 1, input_dim)
        x = x.unsqueeze(1)

        # Conv → BatchNorm → ReLU → Dropout
        x = self.conv(x)  # (batch_size, hidden_dim, input_dim)
        x = self.bn(x)
        x = F.relu(x)
        x = self.dropout(x)

        # Global pooling: (batch_size, hidden_dim, 1)
        x = self.pool(x)

        # Remove last dimension: (batch_size, hidden_dim)
        x = x.squeeze(-1)

        return x


class MultiHeadAttention(nn.Module):
    """Multi-head attention for dynamic timeframe weighting.

    Learns to weight different timeframes based on current market conditions.
    For example, during high volatility, may upweight faster timeframes (1min, 5min),
    while during trends, may upweight slower timeframes (4hr, daily).

    Args:
        hidden_dim: Dimension of input features (must match encoder output)
        num_heads: Number of attention heads (default: 4)
        dropout: Dropout probability (default: 0.3)
    """

    def __init__(
        self,
        hidden_dim: int,
        num_heads: int = 4,
        dropout: float = 0.3
    ):
        super().__init__()

        assert hidden_dim % num_heads == 0, "hidden_dim must be divisible by num_heads"

        self.hidden_dim = hidden_dim
        self.num_heads = num_heads
        self.head_dim = hidden_dim // num_heads

        # Query, Key, Value projections
        self.q_proj = nn.Linear(hidden_dim, hidden_dim)
        self.k_proj = nn.Linear(hidden_dim, hidden_dim)
        self.v_proj = nn.Linear(hidden_dim, hidden_dim)

        # Output projection
        self.out_proj = nn.Linear(hidden_dim, hidden_dim)

        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        query: torch.Tensor,
        key: torch.Tensor,
        value: torch.Tensor,
        mask: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Apply multi-head attention.

        Args:
            query: Query tensor of shape (batch_size, seq_len, hidden_dim)
            key: Key tensor of shape (batch_size, seq_len, hidden_dim)
            value: Value tensor of shape (batch_size, seq_len, hidden_dim)
            mask: Optional mask tensor

        Returns:
            Tuple of:
            - Attended features of shape (batch_size, seq_len, hidden_dim)
            - Attention weights of shape (batch_size, num_heads, seq_len, seq_len)
        """
        batch_size = query.size(0)

        # Project Q, K, V
        Q = self.q_proj(query)  # (batch_size, seq_len, hidden_dim)
        K = self.k_proj(key)
        V = self.v_proj(value)

        # Reshape for multi-head: (batch_size, num_heads, seq_len, head_dim)
        Q = Q.view(batch_size, -1, self.num_heads, self.head_dim).transpose(1, 2)
        K = K.view(batch_size, -1, self.num_heads, self.head_dim).transpose(1, 2)
        V = V.view(batch_size, -1, self.num_heads, self.head_dim).transpose(1, 2)

        # Scaled dot-product attention
        # Attention scores: (batch_size, num_heads, seq_len, seq_len)
        scores = torch.matmul(Q, K.transpose(-2, -1)) / np.sqrt(self.head_dim)

        if mask is not None:
            scores = scores.masked_fill(mask == 0, -1e9)

        # Attention weights
        attn_weights = F.softmax(scores, dim=-1)
        attn_weights = self.dropout(attn_weights)

        # Apply attention to values
        # (batch_size, num_heads, seq_len, head_dim)
        attn_output = torch.matmul(attn_weights, V)

        # Reshape back: (batch_size, seq_len, hidden_dim)
        attn_output = attn_output.transpose(1, 2).contiguous().view(
            batch_size, -1, self.hidden_dim
        )

        # Output projection
        output = self.out_proj(attn_output)

        return output, attn_weights


class HierarchicalFusion(nn.Module):
    """Hierarchical fusion layer for combining timeframes from slow→fast.

    Processes timeframes hierarchically:
    1. Start with daily (slowest) encoding
    2. Fuse with 4hr encoding
    3. Fuse with 1hr encoding
    4. Fuse with 15min encoding
    5. Fuse with 5min encoding
    6. Fuse with 1min encoding (fastest)

    Each fusion uses residual connections and layer normalization.

    Args:
        hidden_dim: Dimension of encoded features
        num_timeframes: Number of timeframes to fuse
        dropout: Dropout probability
    """

    def __init__(
        self,
        hidden_dim: int,
        num_timeframes: int,
        dropout: float = 0.3
    ):
        super().__init__()

        self.hidden_dim = hidden_dim
        self.num_timeframes = num_timeframes

        # Fusion layers for each hierarchical step
        self.fusion_layers = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_dim * 2, hidden_dim),
                nn.LayerNorm(hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout)
            )
            for _ in range(num_timeframes - 1)
        ])

    def forward(self, timeframe_encodings: torch.Tensor) -> torch.Tensor:
        """Fuse timeframe encodings hierarchically.

        Args:
            timeframe_encodings: Tensor of shape (batch_size, num_timeframes, hidden_dim)
                                Ordered from fastest to slowest timeframe

        Returns:
            Fused representation of shape (batch_size, hidden_dim)
        """
        batch_size = timeframe_encodings.size(0)

        # Start with slowest timeframe (last in sequence)
        fused = timeframe_encodings[:, -1, :]  # (batch_size, hidden_dim)

        # Fuse from slow to fast (reverse order)
        for i in range(self.num_timeframes - 2, -1, -1):
            faster_tf = timeframe_encodings[:, i, :]  # (batch_size, hidden_dim)

            # Concatenate and fuse
            combined = torch.cat([fused, faster_tf], dim=1)  # (batch_size, hidden_dim * 2)
            fused = self.fusion_layers[i](combined)  # (batch_size, hidden_dim)

        return fused


class HierarchicalTimeframeNet(nn.Module):
    """Complete hierarchical multi-timeframe neural network.

    Architecture:
    1. Input: Multi-timeframe feature vector (330 TF features + 8 cross-TF features)
    2. TimeframeEncoder: Separate CNN for each timeframe
    3. Multi-head attention: Dynamic timeframe weighting
    4. Hierarchical fusion: Combine slow→fast timeframes
    5. Cross-timeframe feature integration
    6. Classification head: Buy/Hold/Sell prediction

    Args:
        num_timeframes: Number of timeframes (default: 6)
        features_per_tf: Features per timeframe (default: 55)
        cross_tf_features: Number of cross-timeframe features (default: 8)
        hidden_dim: Hidden dimension for encoders (default: 128)
        num_heads: Number of attention heads (default: 4)
        dropout: Dropout probability (default: 0.3)
        num_classes: Number of output classes (default: 3 for Buy/Hold/Sell)

    Example:
        >>> model = HierarchicalTimeframeNet()
        >>> x = torch.randn(32, 338)  # Batch of 32 samples, 338 features
        >>> logits = model(x)  # Shape: (32, 3)
        >>> predictions = torch.argmax(logits, dim=1)  # Shape: (32,)
    """

    def __init__(
        self,
        num_timeframes: int = 6,
        features_per_tf: int = 55,
        cross_tf_features: int = 8,
        hidden_dim: int = 128,
        num_heads: int = 4,
        dropout: float = 0.3,
        num_classes: int = 3
    ):
        super().__init__()

        self.num_timeframes = num_timeframes
        self.features_per_tf = features_per_tf
        self.cross_tf_features = cross_tf_features
        self.hidden_dim = hidden_dim
        self.num_classes = num_classes

        # Total input features: (55 × 6) + 8 = 338
        self.total_tf_features = num_timeframes * features_per_tf
        self.total_features = self.total_tf_features + cross_tf_features

        # Timeframe encoders (one per timeframe)
        self.encoders = nn.ModuleList([
            TimeframeEncoder(
                input_dim=features_per_tf,
                hidden_dim=hidden_dim,
                dropout=dropout
            )
            for _ in range(num_timeframes)
        ])

        # Multi-head attention for timeframe weighting
        self.attention = MultiHeadAttention(
            hidden_dim=hidden_dim,
            num_heads=num_heads,
            dropout=dropout
        )

        # Hierarchical fusion
        self.fusion = HierarchicalFusion(
            hidden_dim=hidden_dim,
            num_timeframes=num_timeframes,
            dropout=dropout
        )

        # Cross-timeframe feature processing
        self.cross_tf_proj = nn.Sequential(
            nn.Linear(cross_tf_features, hidden_dim // 2),
            nn.LayerNorm(hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout)
        )

        # Final classification head
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim + hidden_dim // 2, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, num_classes)
        )

        # Initialize weights
        self._init_weights()

        logger.info(
            f"Initialized HierarchicalTimeframeNet: "
            f"{num_timeframes} TFs, {features_per_tf} features/TF, "
            f"{cross_tf_features} cross-TF features, "
            f"hidden_dim={hidden_dim}, heads={num_heads}, "
            f"total_params={sum(p.numel() for p in self.parameters()):,}"
        )

    def _init_weights(self):
        """Initialize model weights using Xavier/He initialization."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Conv1d):
                nn.init.kaiming_normal_(module.weight, mode='fan_out', nonlinearity='relu')
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, (nn.BatchNorm1d, nn.LayerNorm)):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through hierarchical network.

        Args:
            x: Input tensor of shape (batch_size, total_features)
               where total_features = (num_timeframes × features_per_tf) + cross_tf_features
               Features should be ordered: [TF1_feat1...TF1_feat55, TF2_feat1...TF6_feat55, cross_feat1...cross_feat8]

        Returns:
            Logits of shape (batch_size, num_classes)
        """
        batch_size = x.size(0)

        # Split timeframe features and cross-timeframe features
        tf_features = x[:, :self.total_tf_features]  # (batch_size, num_tf × features_per_tf)
        cross_tf_features = x[:, self.total_tf_features:]  # (batch_size, cross_tf_features)

        # Reshape timeframe features: (batch_size, num_timeframes, features_per_tf)
        tf_features = tf_features.view(batch_size, self.num_timeframes, self.features_per_tf)

        # Encode each timeframe separately
        timeframe_encodings = []
        for i in range(self.num_timeframes):
            tf_input = tf_features[:, i, :]  # (batch_size, features_per_tf)
            encoded = self.encoders[i](tf_input)  # (batch_size, hidden_dim)
            timeframe_encodings.append(encoded)

        # Stack encodings: (batch_size, num_timeframes, hidden_dim)
        stacked_encodings = torch.stack(timeframe_encodings, dim=1)

        # Apply multi-head attention for dynamic timeframe weighting
        # Self-attention: query, key, value all from stacked_encodings
        attended, attn_weights = self.attention(
            query=stacked_encodings,
            key=stacked_encodings,
            value=stacked_encodings
        )  # attended: (batch_size, num_timeframes, hidden_dim)

        # Hierarchical fusion from slow→fast timeframes
        fused = self.fusion(attended)  # (batch_size, hidden_dim)

        # Process cross-timeframe features
        cross_tf_encoded = self.cross_tf_proj(cross_tf_features)  # (batch_size, hidden_dim // 2)

        # Combine fused timeframe features with cross-timeframe features
        combined = torch.cat([fused, cross_tf_encoded], dim=1)  # (batch_size, hidden_dim + hidden_dim // 2)

        # Classification
        logits = self.classifier(combined)  # (batch_size, num_classes)

        return logits

    def predict(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Make predictions with confidence scores.

        Args:
            x: Input features of shape (batch_size, total_features)

        Returns:
            Tuple of:
            - Predicted actions of shape (batch_size,) with values 0 (Buy), 1 (Hold), 2 (Sell)
            - Confidence scores of shape (batch_size,) in range [0, 1]
        """
        logits = self.forward(x)
        probabilities = F.softmax(logits, dim=1)

        # Get predicted class and confidence
        confidences, actions = torch.max(probabilities, dim=1)

        return actions, confidences

    def get_attention_weights(self, x: torch.Tensor) -> torch.Tensor:
        """Get attention weights for interpretability.

        Shows which timeframes the model is focusing on for a given input.

        Args:
            x: Input features of shape (batch_size, total_features)

        Returns:
            Attention weights of shape (batch_size, num_heads, num_timeframes, num_timeframes)
        """
        batch_size = x.size(0)

        # Extract timeframe features
        tf_features = x[:, :self.total_tf_features]
        tf_features = tf_features.view(batch_size, self.num_timeframes, self.features_per_tf)

        # Encode timeframes
        timeframe_encodings = []
        for i in range(self.num_timeframes):
            encoded = self.encoders[i](tf_features[:, i, :])
            timeframe_encodings.append(encoded)

        stacked_encodings = torch.stack(timeframe_encodings, dim=1)

        # Get attention weights
        _, attn_weights = self.attention(
            query=stacked_encodings,
            key=stacked_encodings,
            value=stacked_encodings
        )

        return attn_weights
